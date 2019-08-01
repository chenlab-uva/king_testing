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
parser.add_argument('-v', dest='verbose', help="Verbose tests output.")


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


def handle_kings_output(out, separator = "Sorting autosomes..."):
    out = out.decode()
    lines = out.split("\n")
    summary = []
    inside_summary = False
    for line in lines:
        if line is not "":
            if inside_summary: 
                summary.append(line)
            elif line.startswith(separator):
                summary.append(line)
                inside_summary = True
    return summary


def handle_relationship_summary(input):
    summaries = []
    sum = {} 
    in_summary = False
    for line in input: 
        line = line.strip("  ")
        if in_summary: 
            if line.startswith("Pedigree"):  #MZ PO FS 2nd 3rd OTHER
                pedigree = line.split("\t")[1:]
                sum["pedigree"] = pedigree
            if line.startswith("Inference"):  #MZ PO FS 2nd 3rd OTHER
                inference = line.split("\t")[1:]
                sum["inference"] = inference
                in_summary = False
                summaries.append(sum)
                sum = {}
        if line.startswith("Relationship summary"):
            in_summary = True
    return summaries


def prepare_output(input, separator = "Sorting autosomes...", count = None, save = False): 
    out = []
    inside = False
    for line in input[:-1]:
        tmp  = line.strip("  ")
        if count >= 1 and inside:
            count = count -1
            if not save:
                continue
            out.append(line)
            continue
        if tmp.startswith(separator):
            if save: 
                out.append(line)
            count = count -1
            inside = True
            continue
        if tmp is not "" and save == False:
            out.append(line)
    return out


class KingTestCase(unittest.TestCase):
  ##TODO checking if files created by different functions exist
    def format_command(self, param):
        command = ["{}".format(king_exe), "-b",
                   "{}".format(bed), "--prefix", "{}".format(king_path + "/"), "{}".format(param)]
        return command

    def test_related(self): # ibd + kinship 
        cmd = self.format_command("--related")
        # print(cmd)
        out = subprocess.check_output(cmd)
        summary = handle_kings_output(out, "Relationship summary")
        relationships = handle_relationship_summary(summary)
        self.assertEqual(relationships[0]['pedigree'], ['0', '200', '0', '0', '0', '291'], 'Incorrect pedigree.')
        self.assertEqual(relationships[0]['inference'], ['0', '200', '0', '0', '0', '291'], 'Incorrect inference.')
        self.assertEqual(relationships[1]['inference'], ['0', '1', '1', '0'], 'Incorrect inference')
    
    def test_duplicate(self):
        cmd = self.format_command("--duplicate")
        out = subprocess.check_output(cmd)
        output = handle_kings_output(out)
        summary = prepare_output(output, count = 4)
        self.assertEqual(summary, ["No duplicates are found with heterozygote concordance rate > 80%."], "Incorrect duplicates.")

    def test_unrelated(self):
        cmd = self.format_command("--unrelated")
        out = subprocess.check_output(cmd)
        output = handle_kings_output(out, "The following families")
        summary = prepare_output(output, separator="NewFamID", count = 3, save = True)
        result = []
        for line in summary: 
            if line.startswith("  NewFamID"): 
                continue
            line = line.strip("  ")
            line = line.split("     ")
            result.append({line[0] : line[1]})
        self.assertEqual(result[0], {'KING1': 'Y028,Y117'}, "Incorrect unrelated members.")
        self.assertEqual(result[1], {'KING2': '1454,13291'}, "Incorrect unrelated members.")


if __name__ == "__main__":
    options = parser.parse_known_args()[0]
    if options.clean:
        clean_repository()
        sys.exit()
    prepare_tested_data()
    prepare_king_source()
    unittest.main()