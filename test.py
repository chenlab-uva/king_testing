#!/usr/bin/env python3
import sys
import subprocess
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
files_prefix = "test"


parser = argparse.ArgumentParser()
parser.add_argument('-c', dest='clean', action="store_true",
                    default=False, help="Clean directory from previous testing.")
parser.add_argument('-v', action="store_true", help="Verbose tests output.")


def prepare_tested_data():
    print("Preparing tests data ...")
    url = "http://people.virginia.edu/~wc9c/KING/ex.tar.gz"
    handle_tarball(url, "data")
    global data
    global bed
    bed = os.path.join(data, "ex.bed")
    print("Preparing tests data finished.")


def prepare_king_source():
    print("Building KING from source code ...")
    url = "http://people.virginia.edu/~wc9c/KING/KINGcode.tar.gz"
    handle_tarball(url, "king_src")
    king_obj = os.path.join(king_path, "*.cpp")
    # command = ["c++", "-lm", "-O2", "-fopenmp", "-o", "{}".format(king_exe), "{}".format(king_obj), "-lz"]
    # subprocess.run(command, shell=True)
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


def handle_kings_output(out, separator="Sorting autosomes..."):
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
            if line.startswith("Pedigree"):  # MZ PO FS 2nd 3rd OTHER
                pedigree = line.split("\t")[1:]
                sum["pedigree"] = pedigree
            if line.startswith("Inference"):  # MZ PO FS 2nd 3rd OTHER
                inference = line.split("\t")[1:]
                sum["inference"] = inference
                in_summary = False
                summaries.append(sum)
                sum = {}
        if line.startswith("Relationship summary"):
            in_summary = True
    return summaries


def prepare_output(input, separator="Sorting autosomes...", count=None, save=False):
    out = []
    inside = False
    for line in input[:-1]:
        tmp = line.strip("  ")
        if count >= 1 and inside:
            count = count - 1
            if not save:
                continue
            out.append(line)
            continue
        if tmp.startswith(separator):
            if save:
                out.append(line)
            count = count - 1
            inside = True
            continue
        if tmp is not "" and save is False:
            out.append(line)
    return out


class KingTestCase(unittest.TestCase):

    def format_command(self, param):
        command = ["{}".format(king_exe), "-b",
                   "{}".format(bed), "--prefix", "{}".format(os.path.join(king_path, files_prefix)), "{}".format(param)]
        return command

    def run_command(self, fun, exit_stat=False):
        cmd = self.format_command(fun)
        if exit_stat: 
            try:
                grepOut = subprocess.check_output(cmd)                       
            except subprocess.CalledProcessError as grepexc:                                                                                                   
                out = grepexc.returncode
        else: 
            out = subprocess.check_output(cmd)
        return out

    def test_related(self):  # ibd + kinship
        out = self.run_command("--related")
        summary = handle_kings_output(out, "Relationship summary")
        relationships = handle_relationship_summary(summary)
        self.assertEqual(relationships[0]['pedigree'], [
                         '0', '200', '0', '0', '0', '291'], 'Incorrect pedigree.')
        self.assertEqual(relationships[0]['inference'], [
                         '0', '200', '0', '0', '0', '291'], 'Incorrect inference.')
        self.assertEqual(relationships[1]['inference'], [
                         '0', '1', '1', '0'], 'Incorrect inference')

    def test_related_files(self):
        self.assertTrue(os.path.exists(os.path.join(
            king_path, files_prefix + "allsegs.txt")), "IBD SEGs file doesn't exist.")
        self.assertTrue(os.path.exists(os.path.join(
            king_path, files_prefix + ".kin")), "Within-familt kinship data file doesn't exist.")
        self.assertTrue(os.path.exists(os.path.join(
            king_path, files_prefix + ".kin0")), "Between-familt relatives file doesn't exist.")

    def test_duplicate(self):
        out = self.run_command("--duplicate")
        output = handle_kings_output(out)
        summary = prepare_output(output, count=4)
        self.assertEqual(summary, [
                         "No duplicates are found with heterozygote concordance rate > 80%."], "Incorrect duplicates.")

    def test_unrelated(self):
        out = self.run_command("--unrelated")
        output = handle_kings_output(out, "The following families")
        summary = prepare_output(
            output, separator="NewFamID", count=3, save=True)
        result = []
        for line in summary:
            if line.startswith("  NewFamID"):
                continue
            line = line.strip("  ")
            line = line.split("     ")
            result.append({line[0]: line[1]})
        self.assertEqual(
            result[0], {'KING1': 'Y028,Y117'}, "Incorrect unrelated members.")
        self.assertEqual(
            result[1], {'KING2': '1454,13291'}, "Incorrect unrelated members.")

    def test_unrelated_files(self):
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix +
                                                    "unrelated_toberemoved.txt")), "File containing unrelated individials doesn't exist.")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + "unrelated.txt")),
                        "File containing to-be-removed individials doesn't exist.")

    def test_cluster_files(self):
        out = self.run_command("--cluster")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix +
                                                    "updateids.txt")), "File containing updated-if information doesn't exist.")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + "cluster.kin")),
                        "File containing newly clustered families doesn't exist.")

    def test_build(self):
        out = self.run_command("--build")
        output = handle_kings_output(out, "Family KING2:")
        summary = prepare_output(
            output, separator="Family KING2:", count=2, save=True)
        self.assertEqual(
            summary[1], "  RULE FS0: Sibship (NA07045 NA12813)'s parents are (1 2)", "Incorrect parrents in KING2 family.")

    def test_build_files(self):
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + "build.log")),
                        "File containing details of pedigree reconstruction doesn't exist.")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + "updateparents.txt")),
                        "File containing updated parent information doesn't exist.")

    def test_by_sample(self):
        out = self.run_command("--bysample")
        output = handle_kings_output(out, "QC-by-sample starts")
        summary = prepare_output(
            output, separator="QC-by-sample starts", count=2, save=True)
        self.assertEqual(
            summary[1], "There are 200 parent-offspring pairs and 94 trios according to the pedigree.")

    def test_by_sample_files(self):
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix +
                                                    "bySample.txt")), "File containing QC statistics by sample doesn't exist.")

    def test_by_SNP(self):
        self.run_command("--bySNP")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + "bySNP.txt")), "File containing QC statistics by SNP doesn't exist.")

    def test_roh(self):
        self.run_command("--roh")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + ".roh")),
                        "File containing run of homozygosity summary doesn't exist.")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + ".rohseg.gz")),
                        "File containing run of homozygosity segments doesn't exist.")

    def test_autoqc(self): 
        out = self.run_command("--autoqc")
        output = handle_kings_output(out, "Step Description")
        summary = prepare_output(output, separator="Step Description",count=8, save=True)
        sum = []
        for line in summary:
            sum.append(" ".join(line.split()))
        self.assertEqual(sum, ['Step Description Subjects SNPs', '1 Raw data counts 332 18290', '1.1 SNPs with very low call rate < 80% (removed) (0)', '1.2 Monomorphic SNPs (removed) (0)', '1.3 Sample call rate < 95% (removed) (0)', '1.4 SNPs with call rate < 95% (removed) (0)', '3 Generate Final Study Files', "Final QC'ed data 332 18290"], "Incorrect summary of autoQC.")
    
    def test_autoqc_files(self):
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + "_autoQC_Summary.txt")),"File containing QC summary report doesn't exist.")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + "_autoQC_snptoberemoved.txt")),"File containing SNP-removal QC doesn't exist.")
        self.assertTrue(os.path.exists(os.path.join(king_path, files_prefix + "_autoQC_sampletoberemoved.txt")),"File containing Sample-removal QC doesn't exist.")

    def test_mtscore(self): 
        out = self.run_command("--mtscore", exit_stat = True)   
        self.assertNotEqual(out, 0, "Incorrect --mtscore output.") # Assert that command --mtscore with improper arguments throws an exception (fatal error)

    def test_tdt(self): 
        out = self.run_command("--tdt")
        output = handle_kings_output(out, "\x07WARNING")
        summary = prepare_output(output, separator="\x07WARNING", count=2, save=True)
        self.assertEqual(summary[1], "TDT analysis requires parent-affected-offspring trios.", "Incorrect --tdt output.")


if __name__ == "__main__":
    options = parser.parse_known_args()[0]
    if options.clean:
        clean_repository()
        sys.exit()
    prepare_tested_data()
    prepare_king_source()
    unittest.main()
