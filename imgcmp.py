
from PIL import Image, ImageChops, ImageDraw
from time import localtime, strftime
import sys
import math
import Levenshtein
import fnmatch
import os
import re

class BWImageCompare(object):
	"""Compares two images (b/w)."""
 
	_pixel = 255
	_colour = False
 
	def __init__(self, imga, imgb, maxsize=64):
		"""Save a copy of the image objects."""
 
		sizea, sizeb = imga.size, imgb.size
 
		newx = min(sizea[0], sizeb[0], maxsize)
		newy = min(sizea[1], sizeb[1], maxsize)
 
		# Rescale to a common size:
		imga = imga.resize((newx, newy), Image.BICUBIC)
		imgb = imgb.resize((newx, newy), Image.BICUBIC)
 
		if not self._colour:
			# Store the images in B/W Int format
			imga = imga.convert('I')
			imgb = imgb.convert('I')
 
		self._imga = imga
		self._imgb = imgb
 
		# Store the common image size
		self.x, self.y = newx, newy
 
	def _img_int(self, img):
		"""Convert an image to a list of pixels."""
 
		x, y = img.size
 
		for i in xrange(x):
			for j in xrange(y):
				yield img.getpixel((i, j))
 
	@property
	def imga_int(self):
		"""Return a tuple representing the first image."""
 
		if not hasattr(self, '_imga_int'):
			self._imga_int = tuple(self._img_int(self._imga))
 
		return self._imga_int
 
	@property
	def imgb_int(self):
		"""Return a tuple representing the second image."""
 
		if not hasattr(self, '_imgb_int'):
			self._imgb_int = tuple(self._img_int(self._imgb))
 
		return self._imgb_int
 
	@property
	def mse(self):
		"""Return the mean square error between the two images."""
 
		if not hasattr(self, '_mse'):
			tmp = sum((a-b)**2 for a, b in zip(self.imga_int, self.imgb_int))
			self._mse = float(tmp) / self.x / self.y
 
		return self._mse
 
	@property
	def psnr(self):
		"""Calculate the peak signal-to-noise ratio."""
 
		if not hasattr(self, '_psnr'):
			self._psnr = 20 * math.log(self._pixel / math.sqrt(self.mse), 10)
 
		return self._psnr
 
	@property
	def nrmsd(self):
		"""Calculate the normalized root mean square deviation."""
 
		if not hasattr(self, '_nrmsd'):
			self._nrmsd = math.sqrt(self.mse) / self._pixel
 
		return self._nrmsd
 
	@property
	def levenshtein(self):
		"""Calculate the Levenshtein distance."""
 
		if not hasattr(self, '_lv'):
			stra = ''.join((chr(x) for x in self.imga_int))
			strb = ''.join((chr(x) for x in self.imgb_int))
 
			lv = Levenshtein.distance(stra, strb)
 
			self._lv = float(lv) / self.x / self.y
 
		return self._lv
 
 
class ImageCompare(BWImageCompare):
	"""Compares two images (colour)."""
 
	_pixel = 255 ** 3
	_colour = True
 
	def _img_int(self, img):
		"""Convert an image to a list of pixels."""
 
		x, y = img.size
 
		for i in xrange(x):
			for j in xrange(y):
				pixel = img.getpixel((i, j))
				yield pixel[0] | (pixel[1]<<8) | (pixel[2]<<16)
 
	@property
	def levenshtein(self):
		"""Calculate the Levenshtein distance."""
 
		if not hasattr(self, '_lv'):
			stra_r = ''.join((chr(x>>16) for x in self.imga_int))
			strb_r = ''.join((chr(x>>16) for x in self.imgb_int))
			lv_r = Levenshtein.distance(stra_r, strb_r)
 
			stra_g = ''.join((chr((x>>8)&0xff) for x in self.imga_int))
			strb_g = ''.join((chr((x>>8)&0xff) for x in self.imgb_int))
			lv_g = Levenshtein.distance(stra_g, strb_g)
 
			stra_b = ''.join((chr(x&0xff) for x in self.imga_int))
			strb_b = ''.join((chr(x&0xff) for x in self.imgb_int))
			lv_b = Levenshtein.distance(stra_b, strb_b)
 
			self._lv = (lv_r + lv_g + lv_b) / 3. / self.x / self.y
 
		return self._lv
 
 
class FuzzyImageCompare(object):
	"""Compares two images based on the previous comparison values."""
 
	def __init__(self, imga, imgb, lb=1, tol=15):
		"""Store the images in the instance."""
 
		self._imga, self._imgb, self._lb, self._tol = imga, imgb, lb, tol
 
	def compare(self):
		"""Run all the comparisons."""
 
		if hasattr(self, '_compare'):
			return self._compare
 
		lb, i = self._lb, 2
 
		diffs = {
			'levenshtein': [],
			'nrmsd': [],
			'psnr': [],
		}
 
		stop = {
			'levenshtein': False,
			'nrmsd': False,
			'psnr': False,
		}
 
		while not all(stop.values()):
			cmp = ImageCompare(self._imga, self._imgb, i)
 
			diff = diffs['levenshtein']
			if len(diff) >= lb+2 and \
				abs(diff[-1] - diff[-lb-1]) <= abs(diff[-lb-1] - diff[-lb-2]):
				stop['levenshtein'] = True
			else:
				diff.append(cmp.levenshtein)
 
			diff = diffs['nrmsd']
			if len(diff) >= lb+2 and \
				abs(diff[-1] - diff[-lb-1]) <= abs(diff[-lb-1] - diff[-lb-2]):
				stop['nrmsd'] = True
			else:
				diff.append(cmp.nrmsd)
 
			diff = diffs['psnr']
			if len(diff) >= lb+2 and \
				abs(diff[-1] - diff[-lb-1]) <= abs(diff[-lb-1] - diff[-lb-2]):
				stop['psnr'] = True
			else:
				try:
					diff.append(cmp.psnr)
				except ZeroDivisionError:
					diff.append(-1)  # to indicate that the images are identical
 
			i *= 2
 
		self._compare = {
			'levenshtein': 100 - diffs['levenshtein'][-1] * 100,
			'nrmsd': 100 - diffs['nrmsd'][-1] * 100,
			'psnr': diffs['psnr'][-1] == -1 and 100.0 or diffs['psnr'][-1],
		}
 
		return self._compare
 
	def similarity(self):
		"""Try to calculate the image similarity."""
 
		cmp = self.compare()
 
		lnrmsd = (cmp['levenshtein'] + cmp['nrmsd']) / 2
		return lnrmsd
		return min(lnrmsd * cmp['psnr'] / self._tol, 100.0)  # TODO: fix psnr!

def black_or_b(a, b, opacity=0.2):
	a_width, a_height = a.size
	b_width, b_height = b.size
	max_width = (a_width if (a_width > b_width) else b_width)
	max_height = (a_height if (a_height > b_height) else b_height)

	a_new = Image.new('RGB', (max_width,max_height), "green")
	b_new = Image.new('RGB', (max_width,max_height), "blue")

	a_new.paste(a,(0,0))
	b_new.paste(b,(0,0))

	a_new = a_new.convert('L')
	b_new = b_new.convert('L')

	# A or B
	diff = ImageChops.difference(a_new, b_new)

	# Show diff
	new = Image.new('RGB', (max_width,max_height),(255,0,255))
	new.paste(diff, mask=b_new)
	return new

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
				if diffPercentage > 10:
					# Hightlight diff & save
					c = black_or_b(images[test_img], images[target_img])
					print resultDir
					if not os.path.exists(resultDir):
						os.makedirs(resultDir)
					c.save(result_img)

					# Print log
					completeness = (float)(current_file_number)/total_file_number * 100
					compareFile = re.sub('(\A.*?case\\\)', '', imgs[0])
					log = '[%3.0f%%] [Diff: %5.2f%%] %s\n' % (completeness, diffPercentage, compareFile)

					with open(logFileName, "a") as logFile:
						logFile.write(log)
			except:
				etype, message, traceback = sys.exc_info()
				logError = "[ERROR] <%s>: %s\n" % (etype, message)
				with open(logErrorFileName, "a") as logFile:
						logFile.write(logError)
				continue
