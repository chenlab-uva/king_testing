#!/usr/bin/env python3
import sys
import subprocess
import os
import unittest
import argparse
import unittest
import subprocess
import urllib.request
import tarfile
import os
import shutil


cur_dir = os.path.dirname(os.path.realpath(__file__))
king_exe = ""


parser = argparse.ArgumentParser()
parser.add_argument('-l', dest='local', action="store_true", default=False, help="Use local KING installed in this system.")


def prepare_tested_data():
	print("Preparing tests data ...")
	url = "http://people.virginia.edu/~wc9c/KING/ex.tar.gz"
	handle_tarball(url, "data")
	print("Preparinge tests data finished.")


def prepare_king_source():
	print("Preparing KING's source code ...")
	url = "http://people.virginia.edu/~wc9c/KING/KINGcode.tar.gz"
	handle_tarball(url, "king_src")
	king_path = os.path.join(cur_dir, "king_src")
	king_obj = os.path.join(cur_dir, "king_src", "*.cpp")
	os.system("c++ -lm -O2 -fopenmp -o king {} -lz".format(king_obj))
	king_exe = os.path.join(king_path, "king")
	print("Preparing KING's source code finished.")


def handle_tarball(url, dest_dir=None):
	filename = url.rsplit('/', 1)[-1]
	urllib.request.urlretrieve(url, filename)
	if tarfile.is_tarfile(filename):
		tar = tarfile.open(filename)
		if os.path.exists(dest_dir):
			shutil.rmtree(dest_dir)
		os.makedirs(dest_dir)
		tar.extractall(dest_dir)
		os.remove(filename)


class KingTestCase(unittest.TestCase):
	def setUp(self):
		prepare_tested_data()
		prepare_king_source()
	def test_default_widget_size(self):
		self.assertEqual((50,50), (50,50), 'incorrect default size')

if __name__=="__main__":
    options = parser.parse_args()
    unittest.main()
