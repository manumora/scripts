import os
import time
import re
import subprocess
import datetime

path = '/home/manu/Imprimir/'
output = "%soutput.txt" % path

with open('%scopies.txt' % path) as f:
    number = f.read()

number = re.sub("[^a-z0-9]+","", number, flags=re.IGNORECASE)
number = number if number else 1

some_executed = False

for file in os.listdir(path):
    if file not in ["copies.txt", "output.txt"]:
        if some_executed == False:
            f_output = open(output, "a")
            f_output.write("\n\n##################### %s #####################\n\n" % datetime.datetime.now())

        file_path = "%s%s" % (path, file)
        if os.path.isfile(file_path):
            f_output.write(" --- %s ---\n\n" % file_path)
            try:
                #bashCommand = "lp -n %s '%s'" % (number, file_path)
                process = subprocess.Popen(["lp", "-n", number, file_path], stdout=subprocess.PIPE)
                output, error = process.communicate()
                f_output.write("OUTPUT: %s\n" % output)
                f_output.write("ERROR: %s\n" % error)
                os.remove(file_path)
                time.sleep(10)
            except Exception as e:
                f_output.write("Exception: %s\n" % e)
        else:
            f_output.write("ALERT: is not a file, so can not be printed!: %s\n" % file_path)
        some_executed = True

if some_executed:
    time.sleep(60)
    p1 = subprocess.Popen("lpstat -W completed".split(), stdout=subprocess.PIPE)
    process = subprocess.Popen("head -10".split(), stdin=p1.stdout, stdout=subprocess.PIPE)
    output, error = process.communicate()
    f_output.write("\n--- Last printed files ---\n\n%s" % output)
    f_output.close()