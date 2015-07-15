from time import localtime, strftime
import sys
import fnmatch
import os
import re

# Extra libraries
from lib.caldiff import *
import numpy
import cv2

if __name__ == '__main__':
	point_table = ([0] + ([255] * 255))
	matches = []
	current_file_number = 0
	PATH = '.\\compare\\test_case\\'
	for dirPath, dirName, filename in os.walk(PATH):
		for filename in fnmatch.filter(filename, '*.jpg'):
			matches.append(os.path.join(dirPath, filename))

	total_file_number = len(matches)

	# Create log file
	logTime = strftime("%Y-%m-%d_%H_%M_%S", localtime())
	os.makedirs(logTime)

	logFileName = strftime(".\\"+logTime+"\\log.txt")
	logFile = open(logFileName, 'w')
	logFile.close()
	logErrorFileName = strftime(".\\"+logTime+"\\log_err.txt")
	logErrorFile = open(logErrorFileName, 'w')
	logErrorFile.close()

	# Open comparing images
	for test_img in matches:
		# This number is used to calculate the progress percentage.
		current_file_number = current_file_number + 1

		target_img = test_img.replace("test_case", "sample_case")
		result_img = test_img.replace("compare\\test_case", logTime)

		# Check compare image existence
		if not os.path.isfile(target_img) or not os.path.isfile(test_img):
			# print '[Error] File not exist: {0}'.format(target_img)
			continue
		else:
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
				if diffPercentage > 0:
					# Hightlight diff & save
					resultDir = os.path.split(result_img)[0]
					if not os.path.exists(resultDir):
						os.makedirs(resultDir)
					im = cv2.imread(test_img)
					im1 = cv2.imread(target_img)

					imgray = cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
					ret,thresh = cv2.threshold(imgray,127,255,0)
					image, contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

					cv2.drawContours(im1, contours, -1, (255,0,255), 1)
					cv2.imwrite(result_img, im1)

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