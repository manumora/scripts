#!/usr/bin/env python

from pyramid.paster import get_appsettings
from sqlalchemy import engine_from_config
from sqlalchemy import or_
from insight2.log import Logger
from insight2.smartscribe.views import SmartScribeTranscriptionKeywords, SmartscribeCalculateScoring
from insight2.models.orm import DBSession
from insight2.models.smartscribe import SmartscribeTranscription, SmartscribeKeyword, SmartscribeCategory
from insight2.models.core import Customer
from insight2.models.numbers import Numbers
from insight2.models.accounts import User
from insight2 import OsEnvironmentConfig
import socket
import sys


class ScoringCalculator(object):
    """!Scoring Calculator"""

    def __init__(self):
        settings = get_appsettings("development.ini")
        settings = OsEnvironmentConfig(settings)
        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)
        self.session = DBSession()
        self.logger = Logger('smartscribe_scoring_calculator', 'smartscribe_scoring_calculator.log')
        self.logger.info("Starting script")
        self.errors = False
        self.monitor = Logger('smartscribe_scoring_calculator_monitor', 'smartscribe_scoring_calculator.monit')
        self.all_keywords = {}
        self.all_variants = {}

    def set_monit_state(self, error=False, success=False):
        if success and not self.errors:
            self.monitor.info("Success")
        elif error and not self.errors:
            self.errors = True
            self.monitor.error("Error")

    def get_all_keywords(self):
        """!Get all keywords from database which meet requirements
        @retrun SQLAlchemy object with transcriptions
        """
        keywords = self.session.query(SmartscribeKeyword)\
            .filter(SmartscribeKeyword.is_active == True)\
            .filter(SmartscribeCategory.is_active == True)\
            .filter(SmartscribeCategory.negative != True)\
            .filter(SmartscribeKeyword.negative != True)\
            .filter(SmartscribeKeyword.category_id == SmartscribeCategory.id)\
            .filter(SmartscribeKeyword.deleted == None)\
            .filter(SmartscribeCategory.deleted == None)\
            .all()
        if keywords:
            for keyword in keywords:
                variants = []
                if keyword.customer_id not in self.all_keywords.keys():
                    self.all_keywords.update({keyword.customer_id: []})
                    self.all_variants.update({keyword.customer_id: {}})

                if keyword.name.encode("utf-8").lower() not in self.all_variants[keyword.customer_id]:
                    self.all_variants[keyword.customer_id].update({keyword.name.encode("utf-8").lower(): []})

                if keyword.variants:
                    for key, value in keyword.variants.iteritems():
                        if value["state"] == "True":
                            variants.append(value["name"].lower())
                            if value["name"].lower() != keyword.name.encode("utf-8").lower():
                                self.all_variants[keyword.customer_id][keyword.name.encode("utf-8").lower()].append(value["name"].lower())
                total_score = 0
                if keyword.total_score:
                    total_score = keyword.total_score
                self.all_keywords[keyword.customer_id].append({'category_id': keyword.category_id, 'score': total_score, 'keyword_id': keyword.id, 'keyword': keyword.name.lower(), 'variants': variants})

    def get_customer_keywords_scores(self, customer_id):
        """!Get the keywords of given customer
        @retrun list of customer keywords
        """
        if customer_id in self.all_keywords.keys():
            return self.all_keywords[customer_id]
        return None

    def get_customer_keywords(self, customer_id):
        """!Get the keywords of given customer
        @retrun list of customer keywords
        """
        if customer_id in self.all_keywords.keys():
            keywords = []
            for keyword in self.all_keywords[customer_id]:
                keywords.append(keyword["keyword"])
            return keywords
        return None

    def get_missing_keywords(self, transcription_keywords, selected_words, customer_variants):
        """!Get the keywords which are not present in the transcription
        @retrun list of missing keywords
        """
        """missing_keywords = []
        used_keywords = []
        for keyword in selected_words:
            if not any(d.get('name', None) == keyword for d in transcription_keywords):
                if keyword not in used_keywords:
                    missing_keywords.append(dict(name=keyword, count=0))
                    used_keywords.append(keyword)
        return missing_keywords"""

        missing_keywords = []
        missing_variants = []
        for keyword in selected_words:
            if not any(d.get('name', None).lower() == keyword.lower() for d in transcription_keywords):
                if keyword.decode('utf-8').lower() not in missing_keywords:
                    missing_keywords.append(keyword.decode('utf-8').lower())
                if keyword.decode('utf-8').lower() in customer_variants.keys():
                    missing_variants.extend(customer_variants[keyword.decode('utf-8').lower()])

        return missing_keywords, missing_variants

    def get_transcription_keywords(self, transcription, selected_words, customer_variants, channel=None):
        """!Get the keywords which are present in the transcription
        @retrun list of keywords
        """
        transcription_keywords = SmartScribeTranscriptionKeywords(transcription, selected_words, customer_variants, channel).get_transcription_keywords()

        missing_keywords, missing_variants = self.get_missing_keywords(transcription_keywords, selected_words, customer_variants)

        transcription_variants = SmartScribeTranscriptionKeywords(transcription, missing_variants, customer_variants, channel).get_transcription_keywords()

        for t in transcription_variants:
            for key, value in customer_variants.iteritems():
                if t["name"].lower() in value:
                    transcription_keywords.append({'count': 0, 'variants': [t], 'times': '[]', 'speakers': [], 'name': key.lower()})
        return transcription_keywords, missing_keywords, missing_variants

    def update_transcription(self, transcription, score_keywords, total_score):
        """!Calculate the total score of each category
        @retrun the list which contains total score, categories score and keywords score
        """
        if transcription:
            try:
                transcription.score_update = False
                transcription.score_keywords = score_keywords
                transcription.total_score = total_score
                self.session.add(transcription)
                self.session.flush()
            except Exception:
                self.set_monit_state(error=True)
                self.logger.error("Error updating transcription %s: " % transcription.id)

    def process_transcriptions(self, transcriptions):
        """!Process all transcriptions rows which meet requirements
        @param SQLAlchemy object with transcriptions
        """
        self.get_all_keywords()
        if transcriptions:
            for t in transcriptions:
                self.logger.info("Processing transcription: %s" % t.id)
                #try:
                customer_keywords_scores = self.get_customer_keywords_scores(t.customer_id)
                customer_keywords = self.get_customer_keywords(t.customer_id)
                customer_variants = self.all_variants[t.customer_id]

                if customer_keywords_scores:
                    transcription_keywords, missing_keywords, missing_variants = self.get_transcription_keywords(t.transcription, customer_keywords, customer_variants)
                    score_keywords_both, total_score_both = SmartscribeCalculateScoring(transcription_keywords, missing_keywords, customer_variants, customer_keywords_scores).calculate_categories_scoring()

                    transcription_keywords, missing_keywords, missing_variants = self.get_transcription_keywords(t.transcription, customer_keywords, customer_variants, "left")
                    score_keywords_left, total_score_left = SmartscribeCalculateScoring(transcription_keywords, missing_keywords, customer_variants, customer_keywords_scores).calculate_categories_scoring()

                    transcription_keywords, missing_keywords, missing_variants = self.get_transcription_keywords(t.transcription, customer_keywords, customer_variants, "right")
                    score_keywords_right, total_score_right = SmartscribeCalculateScoring(transcription_keywords, missing_keywords, customer_variants, customer_keywords_scores).calculate_categories_scoring()

                    score_keywords = dict(both=score_keywords_both, left=score_keywords_left, right=score_keywords_right)

                    self.update_transcription(t, score_keywords, total_score_both)
                """except Exception:
                    self.set_monit_state(error=True)
                    self.logger.error("Error processing transcription %s: " % t.id)"""

    def get_transcriptions(self):
        """!Get transcriptions from database which meet requirements
        @retrun SQLAlchemy object with transcriptions
        """
        return self.session.query(SmartscribeTranscription)\
            .filter(SmartscribeTranscription.transcription != None)\
            .filter(SmartscribeTranscription.score_update == True)\
            .filter(SmartscribeTranscription.deleted == None)\
            .all()

    def main(self):
        """!Main method of class
        """
        transcriptions = self.get_transcriptions()
        if transcriptions:
            self.process_transcriptions(transcriptions)
        else:
            self.logger.info("Transcriptions to process not found")
        self.logger.info("Ending script")
        self.set_monit_state(success=True)


def get_lock(process_name):
    global lock_socket
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + process_name)
    except socket.error:
        print 'Scoring calculator Processed Status script is already running, exiting.'
        sys.exit()


if __name__ == '__main__':
    get_lock('insight2_smartscribe_scoring_calculator')
    ScoringCalculator().main()
