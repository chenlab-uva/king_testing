#!/usr/bin/env python3
import os
import sys
import shutil
import tarfile
import unittest
import argparse
import subprocess
import urllib.request


parser = argparse.ArgumentParser()
parser.add_argument('-c', '--clean', dest='clean', action="store_true",
                    default=False, help="Clean directory from previous testing.")
parser.add_argument('-v', '--verbose', action="store_true",
                    help="Verbose tests output.")
parser.add_argument('-d', '--data', action="store_true", dest="data",
                    help="Prepare data without building and testing.")
parser.add_argument('-e', '--exe', action="store", dest="exe",
                    help="Specify KING executable to be used for testing.")


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
    handle_tarball(url, king_path)
    king_obj = os.path.join(king_path, "*.cpp")
    os.system("c++ -lm -O2 -fopenmp -o {} {} -lz".format(king_exe, king_obj))
    print("Preparing KING's source code finished.")


def handle_tarball(url, dest_dir=None):
    filename = url.rsplit('/', 1)[-1]
    urllib.request.urlretrieve(url, filename)
    if tarfile.is_tarfile(filename):
        tar = tarfile.open(filename)
        prepare_directory(dest_dir)
        tar.extractall(dest_dir)
        os.remove(filename)


def prepare_directory(dest_dir):
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir)


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
                out = subprocess.check_output(cmd)
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
        out_file1 = os.path.join(king_path, files_prefix + "allsegs.txt")
        self.assertTrue(os.path.exists(out_file1),
                        "IBD SEGs file doesn't exist.")
        self.assertTrue(os.stat(out_file1).st_size >
                        0, "IBD SEGs file is empty.")
        out_file2 = os.path.join(king_path, files_prefix + ".kin")
        self.assertTrue(os.path.exists(out_file2),
                        "Within-family kinship data file doesn't exist.")
        self.assertTrue(os.stat(out_file2).st_size > 0,
                        "Within-family kinship data file is empty.")
        out_file3 = os.path.join(king_path, files_prefix + ".kin0")
        self.assertTrue(os.path.exists(out_file3),
                        "Between-family relatives file doesn't exist.")
        self.assertTrue(os.stat(out_file3).st_size > 0,
                        "Between-family relatives file is empty.")

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
        out_file1 = os.path.join(
            king_path, files_prefix + "unrelated_toberemoved.txt")
        self.assertTrue(os.path.exists(out_file1),
                        "File containing unrelated individuals doesn't exist.")
        self.assertTrue(os.stat(out_file1).st_size > 0,
                        "File containing unrelated individuals is empty.")
        out_file2 = os.path.join(king_path, files_prefix + "unrelated.txt")
        self.assertTrue(os.path.exists(
            out_file2), "File containing to-be-removed individuals doesn't exist.")
        self.assertTrue(os.stat(out_file1).st_size > 0,
                        "File containing to-be-removed individuals is empty.")

    def test_cluster_files(self):
        out = self.run_command("--cluster")
        out_file1 = os.path.join(king_path, files_prefix + "updateids.txt")
        self.assertTrue(os.path.exists(out_file1),
                        "File containing update-id information doesn't exist.")
        self.assertTrue(os.stat(out_file1).st_size > 0,
                        "File containing update-id information is empty.")
        out_file2 = os.path.join(king_path, files_prefix + "cluster.kin")
        self.assertTrue(os.path.exists(
            out_file2), "File containing newly clustered families doesn't exist.")
        self.assertTrue(os.stat(out_file2).st_size > 0,
                        "File containing newly clustered families is empty.")

    def test_build(self):
        out = self.run_command("--build")
        output = handle_kings_output(out, "Family KING2:")
        summary = prepare_output(
            output, separator="Family KING2:", count=2, save=True)
        self.assertEqual(
            summary[1], "  RULE FS0: Sibship (NA07045 NA12813)'s parents are (1 2)", "Incorrect parrents in KING2 family.")

    def test_build_files(self):
        out_file = os.path.join(king_path, files_prefix + "build.log")
        self.assertTrue(os.path.exists(
            out_file), "File containing details of pedigree reconstruction doesn't exist.")
        self.assertTrue(os.stat(out_file).st_size > 0,
                        "File containing details of pedigree reconstruction is empty.")
        out_file2 = os.path.join(king_path, files_prefix + "updateparents.txt")
        self.assertTrue(os.path.exists(
            out_file2), "File containing updated parent information doesn't exist.")
        self.assertTrue(os.stat(out_file2).st_size > 0,
                        "File containing updated parent information is empty.")

    def test_by_sample(self):
        out = self.run_command("--bysample")
        output = handle_kings_output(out, "QC-by-sample starts")
        summary = prepare_output(
            output, separator="QC-by-sample starts", count=2, save=True)
        self.assertEqual(
            summary[1], "There are 200 parent-offspring pairs and 94 trios according to the pedigree.")

    def test_by_sample_files(self):
        out_file = os.path.join(king_path, files_prefix + "bySample.txt")
        self.assertTrue(os.path.exists(out_file),
                        "File containing QC statistics by sample doesn't exist.")
        self.assertTrue(os.stat(out_file).st_size > 0,
                        "File containing QC statistics by sample is empty.")

    def test_by_SNP_files(self):
        self.run_command("--bySNP")
        out_file = os.path.join(king_path, files_prefix + "bySNP.txt")
        self.assertTrue(os.path.exists(out_file),
                        "File containing QC statistics by SNP doesn't exist.")
        self.assertTrue(os.stat(out_file).st_size > 0,
                        "File containing QC statistics by SNP is empty.")

    def test_roh_files(self):
        self.run_command("--roh")
        out_file = os.path.join(king_path, files_prefix + ".roh")
        self.assertTrue(os.path.exists(
            out_file), "File containing run of homozygosity summary doesn't exist.")
        self.assertTrue(os.stat(out_file).st_size > 0,
                        "File containing run of homozygosity summary is empty.")
        out_file2 = os.path.join(king_path, files_prefix + ".rohseg.gz")
        self.assertTrue(os.path.exists(
            out_file2), "File containing run of homozygosity segments doesn't exist.")
        self.assertTrue(os.stat(out_file2).st_size > 0,
                        "File containing run of homozygosity segments is empty.")

    def test_autoqc(self):
        out = self.run_command("--autoqc")
        output = handle_kings_output(out, "Step Description")
        summary = prepare_output(
            output, separator="Step Description", count=8, save=True)
        sum = []
        for line in summary:
            sum.append(" ".join(line.split()))
        self.assertEqual(sum, ['Step Description Subjects SNPs', '1 Raw data counts 332 18290', '1.1 SNPs with very low call rate < 80% (removed) (0)', '1.2 Monomorphic SNPs (removed) (0)',
                               '1.3 Sample call rate < 95% (removed) (0)', '1.4 SNPs with call rate < 95% (removed) (0)', '3 Generate Final Study Files', "Final QC'ed data 332 18290"], "Incorrect summary of autoQC.")

    def test_autoqc_files(self):
        out_file1 = os.path.join(
            king_path, files_prefix + "_autoQC_Summary.txt")
        self.assertTrue(os.path.exists(out_file1),
                        "File containing QC summary report doesn't exist.")
        self.assertTrue(os.stat(out_file1).st_size > 0,
                        "File containing QC summary report is empty.")
        out_file2 = os.path.join(
            king_path, files_prefix + "_autoQC_snptoberemoved.txt")
        self.assertTrue(os.path.exists(out_file2),
                        "File containing SNP-removal QC doesn't exist.")
        self.assertTrue(os.stat(out_file2).st_size > 0,
                        "File containing SNP-removal QC report is empty.")
        out_file3 = os.path.join(
            king_path, files_prefix + "_autoQC_sampletoberemoved.txt")
        self.assertTrue(os.path.exists(out_file3),
                        "File containing Sample-removal QC doesn't exist.")
        self.assertTrue(os.stat(out_file3).st_size > 0,
                        "File containing Sample-removal QC is empty.")

    def test_mtscore(self):
        out = self.run_command("--mtscore", exit_stat=True)
        # Assert that command with improper arguments throws an exception (fatal error)
        self.assertNotEqual(out, 0, "Incorrect --mtscore output.")

    def test_tdt(self):
        out = self.run_command("--tdt")
        output = handle_kings_output(out, "\x07WARNING")
        summary = prepare_output(
            output, separator="\x07WARNING", count=2, save=True)
        self.assertEqual(
            summary[1], "TDT analysis requires parent-affected-offspring trios.", "Incorrect --tdt output.")

    def test_risk(self):
        out = self.run_command("--risk", exit_stat=True)
        # Assert that command with improper arguments throws an exception (fatal error)
        self.assertNotEqual(out, 0, "Incorrect --risk output.")

    @unittest.skip("Not able to call --cpus from Python.")
    def test_cpus(self):
        out = self.run_command("--cpus")
        output = handle_kings_output(out, "Relationship inference")
        summary = prepare_output(
            output, separator="2 CPU cores are used", count=1, save=True)
        self.assertEqual(
            summary[0], "2 CPU cores are used...", "Incorrect number of cpus used.")

    def test_pca(self):
        out = self.run_command("--pca")
        if "SVD...  Please re-compile KING with LAPACK library." in out.decode():
            print("Binary compiled without LAPACK. Skipping PCA test ...")
            return 
        output = handle_kings_output(out, "SVD...  LAPACK is used.")
        summary = prepare_output(
            output, separator="SVD...  LAPACK is used.", count=2, save=True)
        self.assertEqual(
            summary[1], "Largest 20 eigenvalues: 828.95 160.64 158.81 148.44 145.73 144.82 143.56 143.08 143.01 142.91 142.60 142.15 142.01 141.80 141.69 141.62 141.28 141.08 140.94 140.72", "Incorrect pca analysis.")

    def test_pcs_files(self):
        out_file1 = os.path.join(king_path, files_prefix + "pc.txt")
        self.assertTrue(os.path.exists(out_file1),
                        "File containing principal components doesn't exist.")
        self.assertTrue(os.stat(out_file1).st_size > 0,
                        "File containing principal components is empty.")

    def test_mds(self):
        out = self.run_command("--mds")
        if "  Please re-compile KING with LAPACK library." in out.decode():
            print("Binary compiled without LAPACK. Skipping MDS test ...")
            return
        output = handle_kings_output(out, "  LAPACK is being used...")
        summary = prepare_output(
            output, separator="LAPACK is being used...", count=2, save=True)
        self.assertEqual(
            summary[1], "Largest 20 eigenvalues: 27.66 1.05 1.00 0.94 0.91 0.90 0.89 0.89 0.88 0.88 0.88 0.88 0.87 0.87 0.87 0.87 0.86 0.86 0.86 0.85", "Incorrect mds analysis.")

    def test_mds_files(self):
        out_file1 = os.path.join(king_path, files_prefix + "pc.txt")
        self.assertTrue(os.path.exists(out_file1),
                        "File containing principal components doesn't exist.")
        self.assertTrue(os.stat(out_file1).st_size > 0,
                        "File containing principal components is empty.")


if __name__ == "__main__":
    global king_exe, cur_dir, king_path, data, bed, files_prefix
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    king_path = os.path.join(cur_dir, "king_src")
    data = os.path.join(cur_dir, "data")
    bed = "ex.bed"
    files_prefix = "test"

    options = parser.parse_known_args()[0]

    if options.clean:
        clean_repository()
        sys.exit()
    if options.data:
        prepare_tested_data()
        sys.exit()
    if options.exe:
        if os.path.exists(options.exe):
            prepare_directory(king_path)
            king_exe = options.exe
            # Delete "-e" argument from arguments list to prevent unittest errors - it is script argument not unittests argument
            for x in range(0, len(sys.argv)):
                if sys.argv[x] == "-e":
                    # Pop "-e" and path to binary from arguments list
                    sys.argv.pop(x+1)
                    sys.argv.pop(x)
                    break
        else:
            print("Specified path to KING executable doesn't exist.")
            sys.exit(1)
    else:
        king_exe = os.path.join(king_path, "king")
        prepare_king_source()

    prepare_tested_data()
    unittest.main()
