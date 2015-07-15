
from time import localtime, strftime
import sys
import fnmatch
import os
import re

# Extra library
from lib.caldiff import *
from lib.imgdiff import *


if __name__ == '__main__':
	point_table = ([0] + ([255] * 255))
	matches = []
	current_file_number = 0
	PATH = '.\\compare\\test_case\\'
	for dirPath, dirName, filename in os.walk(PATH):
		for filename in fnmatch.filter(filename, '*.jpg'):
			matches.append(os.path.join(dirPath, filename))

	total_file_number = len(matches)

	# Create log files:
	logTime = strftime("%Y-%m-%d_%H_%M_%S", localtime())
	os.makedirs(logTime)

	logFileName = strftime(".\\"+logTime+"\\log.txt")
	logFile = open(logFileName, 'w')
	logFile.close()
	logErrorFileName = strftime(".\\"+logTime+"\\log_err.txt")
	logErrorFile = open(logErrorFileName, 'w')
	logErrorFile.close()

	#
	# Start compare
	#
	for test_img in matches:
		# current_file_number is used to calculate the progress percentage.
		current_file_number = current_file_number + 1

		# Set sample and result filename
		target_img = test_img.replace("test_case", "sample_case")
		result_img = test_img.replace("compare\\test_case", logTime)

		# Check if compare image existence
		if not os.path.isfile(target_img):
			logError = "[ERROR] File not exists: %s\n" % (target_img)
			with open(logErrorFileName, "a") as logFile:
				logFile.write(logError)
			continue
		elif not os.path.isfile(test_img):
			logError = "[ERROR] File not exists: %s\n" % (test_img)
			with open(logErrorFileName, "a") as logFile:
				logFile.write(logError)
			continue
		else:
		# Start compare process
			try:
				images = {}
				images[test_img] = Image.open(test_img)
				images[target_img] = Image.open(target_img)

				results, i = {}, 1
				for namea, imga in images.items():
					for nameb, imgb in images.items():
						if namea == nameb or (nameb, namea) in results:
							continue

						cmp = FuzzyImageCompare(imga, imgb)
						sim = cmp.similarity()
						results[(namea, nameb)] = sim
			 
						i += 1

				# Calculate difference
				res = max(results.values())
				imgs = [k for k, v in results.iteritems() if v == res][0]
				diffPercentage = 100-res

				# If difference large than (4 %), log & save diff picture.
				if diffPercentage > 4:
					if diffPercentage < 20:
						# Hightlight diff & save result picture

						# Check result path exist?
						resultDir = os.path.split(result_img)[0]
						if not os.path.exists(resultDir):
							os.makedirs(resultDir)

						# Draw Highlight
						opts = ['-S', '--opacity', '20', '-o', result_img]
						imgdiff(test_img, target_img, opts)

					# Print log
					completeness = (float)(current_file_number)/total_file_number * 100
					compareFile = re.sub('(\A.*?case\\\)', '', imgs[0])
					log = '[%3.0f%%] [Diff: %5.2f%%] %s\n' % (completeness, diffPercentage, compareFile)
					print log
					with open(logFileName, "a") as logFile:
						logFile.write(log)
			except:
				etype, message, traceback = sys.exc_info()
				logError = "[ERROR] <%s>: %s\n" % (etype, message)
				with open(logErrorFileName, "a") as logFile:
						logFile.write(logError)
				continue