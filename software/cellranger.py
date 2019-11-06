import subprocess
import os
import random
from interface.fastqdirectory import FastQDirectory

from utils.config import Configuration

config = Configuration()

class CellRanger(object):

    @staticmethod
    def cmd(command, args):
        cmd = ["cellranger", command]
        for flag, value in args.items():
            cmd.append("--{}".format(flag)
            )
            cmd.append(value)
        # if config.lsf:
        #     cmd.append("--jobmode=lsf")
        #     cmd.append("--maxjobs=200")
        cmd.append("--disable-ui")
        cmd.append("--localcores 32")
        cmd.append("--localmem 128")
        return cmd

    @staticmethod
    def mro(fastqs, mrofile):
        sample_json = dict()
        content = """
        @include "sc_rna_counter.cs.mro"
        call SC_RNA_COUNTER_CS(
            sample_id = {sample_id},
            sample_def = [
                {sample_definitions}
            ],
            sample_desc = "",
            reference_path = {reference},
            recovered_cells = null,
            force_cells = null,
            no_secondary_analysis = false,
        )"""
        sample_definitions = list()
        for fastq in fastqs:
            definition = dict()
            defintion["fastq_mode"] = "ILMN_BCL2FASTQ"
            definition["gem_group"] = "null",
            definition["lanes"] = "null",
            definition["read_path"] = fastq.path
            definition["sample_indices"] = '["any"]'
            definition["sample_names"] = '[" ' + fastq.sampleid + ' "]'
            sample_definitions.append(definition)
        output = open(mrofile, "w")
        output.write(content.format(sample_id=run_id, sample_definitions=sample_definitions, reference=config.reference))
        output.close()


    @staticmethod
    def mkfastq(bcl_object):
        args = dict()
        args["id"] = bcl_object.id
        args["run"] = bcl_object.path
        args["csv"] = bcl_object.csv
        cmd = CellRanger.cmd("mkfastq",args)
        subprocess.call(cmd)
        return FastQDirectory(bcl_object.out())

    @staticmethod
    def aggr(csv, prefix):
        args = dict()
        args["id"] = "run_{}".format(prefix)
        args["csv"] = csv
        args["normalize"] = "none"
        cmd = CellRanger.cmd("aggr",args)
        subprocess.call(cmd)

    @staticmethod
    def count(fastqs, reference_override=False):
        print("Running Cellranger")
        fastqs = [FastQDirectory(fastq, config.prefix, config.jobpath, config.datapath) for fastq in fastqs]
        args = dict()
        fastq_files = []
        args["id"] = "_".join([fastq.id for fastq in fastqs])
        paths = [fastq.path for fastq in fastqs]
        args["fastqs"] = ",".join(paths)
        try:
            args["sample"] = ",".join([fastq.samples.sampleid[0] for fastq in fastqs])
        except Exception as e:
            pass
        args["transcriptome"] = config.reference
        if reference_override:
            args["transcriptome"] = reference_override
            if "mm10" in args["transcriptome"]:
                script = "cellranger_mouse.sh"
                output = open(script,"w")
                args["id"] += "_mouse"
            else:
                script = "cellranger_human.sh"
                output = open(script,"w")
        else:
            args["transcriptome"] = config.reference
            script = "cellranger_human.sh"
            output = open(script,"w")
        if config.chemistry is not None:
            args["chemistry"] = config.chemistry
        cmd = CellRanger.cmd("count",args)
        print("Saving command to submission script ", " ".join(cmd))
        output.write("source /codebase/cellranger-3.0.2/sourceme.bash\n")
        output.write(" ".join(cmd)+"\n")
        output.close()
        result = subprocess.check_output(["bash",script])
        print("Cellranger exit: {}".format(result))

    @staticmethod
    def reanalyze(tenx_object):
        args = dict()
        args["id"] = tenx_object.id
        args["matrix"] = tenx_object.matrix
        args["params"] = tenx_object.params
        cmd = CellRanger.cmd("reanalyze", args)
        subprocess.call(cmd)
