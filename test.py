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
king_path = os.path.join(cur_dir, "king_src")
data = os.path.join(cur_dir, "data")
bed = "ex.bed"
king_exe = os.path.join(king_path, "king")

parser = argparse.ArgumentParser()
parser.add_argument('-c', dest='clean', action="store_true",
                    default=False, help="Clean directory from previous testing.")


def prepare_tested_data():
    print("Preparing tests data ...")
    url = "http://people.virginia.edu/~wc9c/KING/ex.tar.gz"
    handle_tarball(url, "data")
    global data
    global bed
    bed = os.path.join(data, "ex.bed")
    print("Preparing tests data finished.")


def prepare_king_source():
    print("Preparing KING's source code ...")
    url = "http://people.virginia.edu/~wc9c/KING/KINGcode.tar.gz"
    handle_tarball(url, "king_src")
    king_obj = os.path.join(king_path, "*.cpp")
    #command = ["c++", "-lm", "-O2", "-fopenmp", "-o", "{}".format(king_exe), "{}".format(king_obj), "-lz"]
    #subprocess.run(command, shell=True)
    os.system("c++ -lm -O2 -fopenmp -o {} {} -lz".format(king_exe, king_obj))
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


def clean_repository():
    for pth in [king_path, data]:
        if os.path.exists(pth):
            print("Cleaning {}...".format(pth))
            shutil.rmtree(pth)
    print("Finished")


def handle_kings_output(out):
    out = out.decode()
    lines = out.split("\n")
    # print(lines)
    summary = []
    inside_summary = False
    for line in lines:
        if inside_summary: 
            summary.append(line)
        if line.startswith("Autosome genotypes") or inside_summary:
            inside_summary = True
        
    print("\n".join(summary))


class KingTestCase(unittest.TestCase):
   #def setUp(self):
    #    prepare_tested_data()
     #   prepare_king_source()

    def format_command(self, param):
        command = ["{}".format(king_exe), "-b",
                   "{}".format(bed), "--prefix", "{}".format(king_path + "/"), "{}".format(param)]
        return command

    def test_default_widget_size(self):
        self.assertEqual((50, 50), (50, 50), 'incorrect default size')

    def test_related(self):
        cmd = self.format_command("--related")
        # print(cmd)
        out = subprocess.check_output(cmd)
        handle_kings_output(out)
        self.assertEqual(1, 1, 'wrong')


if __name__ == "__main__":
    options = parser.parse_known_args()[0]
    if options.clean:
        clean_repository()
        sys.exit()
    prepare_tested_data()
    prepare_king_source()
    unittest.main()
