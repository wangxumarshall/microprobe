# Copyright 2011-2021 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""":mod:`microprobe.driver.genetic` module

"""

# TODO: This module is deprecated. Need to reimplement for python 3

# Futures
from __future__ import absolute_import, division, print_function

# Built-in modules
import datetime
import math
import os
import subprocess
import sys
import tempfile
import time as runtime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
import random as pyrandom

# Third party modules


# Own modules
from microprobe.exceptions import MicroprobeError
from microprobe.utils.logger import get_logger
from microprobe.utils.misc import RND as random

# pylint: disable=E0401
# import pyevolve.G1DList  # @UnresolvedImport
# import pyevolve.GAllele  # @UnresolvedImport
# import pyevolve.GSimpleGA  # @UnresolvedImport
# import pyevolve.Initializators  # @UnresolvedImport
# import pyevolve.Mutators  # @UnresolvedImport
# pylint: enable=E0401

# Constants
LOG = get_logger(__name__)
__all__ = [
    "GenericDriver",
    "ExecCmdDriver",
    "EvolutionConfig",
    "EvolutionRecord",
    "SDCFuzzingGeneticDriver",
]

# Functions


# Classes
class GenericDriver(object):
    """Class to represent a Generic DSE Driver."""

    def __init__(self,
                 eval_func,
                 target_score,
                 generations,
                 population,
                 params,
                 allele=False,
                 dummy_slots=False,
                 logfile=None, ):
        """

        :param eval_func:
        :param target_score:
        :param generations:
        :param population:
        :param params:
        :param allele:  (Default value = False)
        :param dummy_slots:  (Default value = False)

        """
        LOG.debug("Population size: %d", population)
        LOG.debug("Target score: %f", target_score)
        LOG.debug("Generations: %d", generations)

        self._allele = None
        self._params = []
        self._ga = None

        raise NotImplementedError(
            "Genetic algorithm was implemented with pyevolve. "
            "Python 3 support has not been added to pyevolve. "
            "This driver only has support for Python2. "
            "Microprobe is a python3 project now.")

        # if not six.PY2:
        #     raise NotImplementedError("Driver support only for Python2")

        # self._allele = allele

        # if allele:

        #     set_of_alleles = pyevolve.GAllele.GAlleles()

        #     length = 0
        #     self._params = []
        #     for param_values in params:
        #         pmin, pmax, pstep = param_values
        #         start = length

        #         for dummy_elem in range(0, int((pmax - pmin) // pstep)):
        #             allele_range = pyevolve.GAllele.GAlleleRange(0, 1)
        #             length += 1
        #             set_of_alleles.add(allele_range)

        #         end = length
        #         self._params.append((pmin, pmax, pstep, start, end))

        #         genome = pyevolve.G1DList.G1DList(length)
        #         genome.setParams(allele=set_of_alleles)

        #         genome.mutator.set(pyevolve.Mutators.G1DListMutatorAllele)
        #         genome.initializator.set(
        #             pyevolve.Initializators.G1DListInitializatorAllele)
        #         genome.crossover.set(
        #             pyevolve.Crossovers.G1DListCrossoverSinglePoint)

        # else:
        #     genome = pyevolve.G1DList.G1DList(len(params))
        #     mmin = min([m[0] for m in params])
        #     mmax = max([M[1] for M in params])
        #     genome.setParams(rangemin=mmin)
        #     genome.setParams(rangemax=mmax)
        #     genome.setParams(gauss_mu=(mmax - mmin) // 2)
        #     genome.setParams(gauss_mu=1)
        #     genome.setParams(gauss_sigma=1)
        #     genome.mutator.set(pyevolve.Mutators.G1DListMutatorRealGaussian)
        #     genome.initializator.set(
        #         pyevolve.Initializators.G1DListInitializatorReal)
        #     genome.crossover.set(self.max_min_cross_over)

        # genome.evaluator.set(eval_func)

        # genome.setParams(bestrawscore=target_score)
        # genome.setParams(roundDecimal=2)

        # ga_obj = pyevolve.GSimpleGA.GSimpleGA(genome)
        # ga_obj.setGenerations(generations)
        # ga_obj.setElitism(False)
        # ga_obj.setMutationRate(0.5)
        # ga_obj.terminationCriteria.set(pyevolve.GSimpleGA.RawScoreCriteria)
        # ga_obj.setPopulationSize(population)
        # ga_obj.setMinimax(pyevolve.Consts.minimaxType["maximize"])

        # self._ga = ga_obj
        # self._results = None
        # if logfile is not None:
        #     if os.path.isfile(logfile):
        #         raise MicroprobeError(f"Log file '{logfile}' already exist")
        #     self._logfile_fd = open(logfile, 'w')

        #     header = "TIME, GENERATION,INDIVIDUAL,%s,SCORE" % ','.join(
        #         ['PARAM%03d' % elem for elem in range(0, len(params))])

        #     self._logfile_fd.write(header + "\n")
        #     pyevolve.logEnable()

        #     def _logging_callback(ga_engine):

        #         generation = ga_engine.getCurrentGeneration()
        #         line = "%f" % runtime.time()
        #         line += ",%03d" % generation
        #         line += ","

        #         for idx, elem in enumerate(ga_engine.getPopulation()):
        #             pline = line + str(idx) + ","
        #             pline += ",".join(
        #                 [str(param) for param in elem.genomeList]
        #             )
        #             pline += "," + str(elem.score)
        #             self._logfile_fd.write(pline + "\n")

        #         return False

        #     self._ga.stepCallback.set(_logging_callback)

    def rejoinparams(self, chromosome):
        """

        :param chromosome:

        """

        if self._allele:
            params = []
            for pmin, dummy_pmax, pstep, start, end in self._params:
                params.append((sum(chromosome[start:end]) * pstep) + pmin)
            return params
        else:
            return chromosome

    def run(self, freq_stats):
        """

        :param freq_stats:

        """
        self._ga.evolve(freq_stats=freq_stats)
        self._results = self._ga.bestIndividual()

    def solution(self):
        """ """
        return self.rejoinparams(self._results.genomeList)

    def score(self):
        """ """
        return self._results.score

    @classmethod
    def max_min_cross_over(cls, dummy_genome, **args):
        """ Max min cross_over.

        :param dummy_genome: arguments
        :param args: arguments

        """
        sister = None
        brother = None
        g_mom = args["mom"]
        g_dad = args["dad"]

        if args["count"] >= 1:
            sister = g_mom.clone()
            sister.resetStats()

            for idx, dummy_elem in enumerate(sister):
                rand = random.randint(-1, 1)
                rand = rand * 0.33
                sister[idx] = ((g_dad[idx] + g_mom[idx]) // 2) + rand

        if args["count"] == 2:
            brother = g_dad.clone()
            brother.resetStats()

            for idx, dummy_elem in enumerate(brother):
                rand = random.randint(-1, 1)
                rand = rand * 0.33
                sister[idx] = ((g_dad[idx] + g_mom[idx]) // 2) + rand

        return (sister, brother)


class ExecCmdDriver(GenericDriver):
    """Class to represent a Command Line DSE Driver"""

    def __init__(self,
                 bench_factory,
                 target_score: int,
                 generations: int,
                 population: int,
                 cmd: str,
                 params,
                 logfile=None):
        """

        :param bench_factory:
        :param target_score:
        :param generations:
        :param population:
        :param cmd:
        :param params:

        """

        def eval_func_factory(function, cmd: str):
            """

            :param function:
            :param cmd:

            """

            def eval_func(chromosome):
                """

                :param chromosome:

                """

                result = []

                sol_eval = 1
                for iteration in range(0, sol_eval):

                    print("Iteration %s" % iteration)
                    file_fd, name = tempfile.mkstemp()
                    dirname = os.path.dirname(name)
                    fname = os.path.basename(name)
                    os.close(file_fd)

                    starttime = runtime.time()
                    print("Start generating...")
                    function(name, *self.rejoinparams(chromosome.genomeList))
                    print("End generating")
                    midtime = runtime.time()
                    print("Start evaluation...")
                    process = subprocess.Popen("%s %s" % (cmd, name),
                                               shell=True,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT)
                    line = process.stdout.readline(
                    )  # pylint: disable=E1101
                    print("End evaluation")
                    endtime = runtime.time()

                    print("Generated: %s" %
                          (datetime.timedelta(seconds=midtime - starttime)))
                    print("Evaluated: %s" %
                          (datetime.timedelta(seconds=endtime - midtime)))
                    print("Total: %s" %
                          (datetime.timedelta(seconds=endtime - starttime)))

                    try:
                        print("Line: '%s'" % line)
                        result.append(float(line))
                    except Exception:

                        print(Exception)
                        print("TODO: Fix exception handling")
                        exit(-1)

                        print("Got wrong line: %s" % line)
                        print("call:", cmd, name)
                        result.append(0)

                    for elem in os.listdir(dirname):
                        if elem.startswith(fname):
                            os.remove("%s/%s" % (dirname, elem))

                result = [math.sqrt(x) for x in result]
                # print chromosome
                # result = sum(chromosome.genomeList)

                result = sum(result) // sol_eval
                # print "Score: %f"%result, self.rejoinparams(
                # chromosome.genomeList)

                return result

            return eval_func

        eval_func = eval_func_factory(bench_factory, cmd)

        super(ExecCmdDriver, self).__init__(eval_func,
                                            target_score,
                                            generations,
                                            population,
                                            params,
                                            allele=False,
                                            logfile=logfile)


@dataclass(frozen=True)
class EvolutionConfig:
    """Configuration for the Python 3 SDC fuzzing evolution loop."""

    parent_limit: int = 8
    offspring_per_parent: int = 2
    max_offspring: int = 16
    sequence_length: int = 8
    benchmark_size: int = 64
    dependency_distance: int = 1
    strict_validation: bool = False
    min_memory_stride: int = 8192
    wrapper_name: str = "Arm64AsmWrapper"
    base_seed: int = 211
    crossover_rate: float = 0.65
    mutation_rate: float = 0.80


@dataclass(frozen=True)
class EvolutionRecord:
    """Description of an offspring emitted by the evolution pass."""

    testcase_key: str
    parent_testcase_keys: tuple[str, ...]
    generation: int
    risk_score: float
    output_file: Optional[str]
    metadata: Dict[str, Any]


_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sdc_agent.generation import (  # noqa: E402
    DEFAULT_POLICY,
    DEFAULT_TARGET,
    collect_sensitive_instructions,
    generate_testcase,
)
from sdc_agent.scheduler import FeedbackScheduler  # noqa: E402
from sdc_agent.vault import SDCVault  # noqa: E402


class SDCFuzzingGeneticDriver(object):
    """Python 3 feedback-driven offspring generator for the SDC vault."""

    _MEMORY_MNEMONICS = ("LDR", "STR", "LDUR", "STUR")

    def __init__(self, config: Optional[EvolutionConfig] = None):
        self.config = config or EvolutionConfig()
        self._scheduler = FeedbackScheduler()

    @staticmethod
    def _extract_generation(metadata: Mapping[str, Any]) -> int:
        lineage = metadata.get("lineage", {})
        return int(lineage.get("generation", 0))

    def _resolve_target_name(
        self,
        parent: Any,
        override_target: Optional[str],
    ) -> str:
        if override_target:
            return override_target
        return str(parent.target_name or DEFAULT_TARGET)

    def _resolve_policy_name(
        self,
        parent: Any,
        override_policy: Optional[str],
    ) -> str:
        if override_policy:
            return override_policy
        return str(parent.policy_name or DEFAULT_POLICY)

    def _fallback_instruction_names(self, target_name: str) -> List[str]:
        from sdc_agent.generation import bootstrap_microprobe_paths
        from microprobe.target import import_definition

        bootstrap_microprobe_paths()
        target = import_definition(target_name)
        return [instruction.name for instruction in collect_sensitive_instructions(target)]

    def _instruction_names_for(self, candidate: Any, target_name: str) -> List[str]:
        names = list(candidate.metadata.get("instruction_names", []))
        if names:
            return [str(name) for name in names]
        return self._fallback_instruction_names(target_name)

    def _memory_instruction_names(self, target_name: str) -> List[str]:
        from sdc_agent.generation import bootstrap_microprobe_paths
        from microprobe.target import import_definition

        bootstrap_microprobe_paths()
        target = import_definition(target_name)
        names = [
            instruction.name
            for instruction in target.isa.instructions.values()
            if instruction.mnemonic.upper() in self._MEMORY_MNEMONICS
        ]
        names.sort()
        return names

    def _mutate_instruction_names(
        self,
        *,
        primary: Sequence[str],
        secondary: Sequence[str],
        seed: int,
        target_name: str,
    ) -> tuple[List[str], List[str]]:
        rng = pyrandom.Random(seed)
        operators: List[str] = []
        sensitive = self._fallback_instruction_names(target_name)
        memory_pool = self._memory_instruction_names(target_name)

        if primary and secondary and rng.random() < self.config.crossover_rate:
            split_primary = max(1, len(primary) // 2)
            split_secondary = max(1, len(secondary) // 2)
            child = list(primary[:split_primary]) + list(secondary[split_secondary:])
            operators.append("one_point_crossover")
        else:
            child = list(primary or secondary)

        if not child:
            child = list(sensitive[: self.config.sequence_length])
            operators.append("bootstrap_sensitive_defaults")

        while len(child) < self.config.sequence_length:
            pool = child or sensitive
            child.append(rng.choice(pool))
            operators.append("length_fill")

        child = child[: self.config.sequence_length]

        if memory_pool:
            slot = rng.randrange(len(child))
            child[slot] = rng.choice(memory_pool)
            operators.append("memory_bias")

        if sensitive and rng.random() < self.config.mutation_rate:
            slot = rng.randrange(len(child))
            child[slot] = rng.choice(sensitive)
            operators.append("opcode_replace")

        return child, operators

    def evolve(
        self,
        vault: SDCVault,
        *,
        output_dir: Optional[Path] = None,
        target_name: Optional[str] = None,
        policy_name: Optional[str] = None,
        parent_limit: Optional[int] = None,
    ) -> List[EvolutionRecord]:
        parent_count = parent_limit or self.config.parent_limit
        parents = self._scheduler.select_candidates(vault, parent_count)
        if not parents:
            return []

        records: List[EvolutionRecord] = []
        emitted = 0

        for index, parent in enumerate(parents):
            if emitted >= self.config.max_offspring:
                break

            partner = parents[(index + 1) % len(parents)] if len(parents) > 1 else parent
            resolved_target = self._resolve_target_name(parent, target_name)
            resolved_policy = self._resolve_policy_name(parent, policy_name)
            primary_names = self._instruction_names_for(parent, resolved_target)
            secondary_names = self._instruction_names_for(partner, resolved_target)
            parent_generation = max(
                self._extract_generation(parent.metadata),
                self._extract_generation(partner.metadata),
            )
            preferred_stride = max(
                int(parent.metadata.get("preferred_stride_bytes", 0) or 0),
                int(partner.metadata.get("preferred_stride_bytes", 0) or 0),
                self.config.min_memory_stride,
            )

            for child_index in range(self.config.offspring_per_parent):
                if emitted >= self.config.max_offspring:
                    break

                child_seed = self.config.base_seed + emitted
                child_names, operators = self._mutate_instruction_names(
                    primary=primary_names,
                    secondary=secondary_names,
                    seed=child_seed,
                    target_name=resolved_target,
                )
                lineage = {
                    "generation": parent_generation + 1,
                    "parents": [parent.testcase_key, partner.testcase_key],
                    "driver": "SDCFuzzingGeneticDriver",
                    "operators": operators,
                    "parent_statuses": [parent.status, partner.status],
                    "parent_fitness": [parent.fitness, partner.fitness],
                }
                metadata_extra = {
                    "requested_profile_name": parent.metadata.get(
                        "requested_profile_name",
                        parent.metadata.get("profile_name", "SIM_SAFE"),
                    ),
                    "profile_name": parent.metadata.get("profile_name", "SIM_SAFE"),
                    "preferred_stride_bytes": preferred_stride,
                    "lineage": lineage,
                }
                generated = generate_testcase(
                    {
                        "target": resolved_target,
                        "policy": resolved_policy,
                        "wrapper": self.config.wrapper_name,
                        "sequence_length": self.config.sequence_length,
                        "benchmark_size": self.config.benchmark_size,
                        "dependency_distance": self.config.dependency_distance,
                        "memory_stream_stride": preferred_stride,
                        "strict_validation": self.config.strict_validation,
                        "profile_name": metadata_extra["requested_profile_name"],
                        "seed": child_seed,
                        "output_dir": str(output_dir) if output_dir is not None else None,
                        "instruction_names": child_names,
                        "metadata_extra": metadata_extra,
                    }
                )
                vault.upsert_testcase(generated["entry"])
                records.append(
                    EvolutionRecord(
                        testcase_key=generated["entry"].testcase_key,
                        parent_testcase_keys=(parent.testcase_key, partner.testcase_key),
                        generation=parent_generation + 1,
                        risk_score=generated["entry"].risk_score,
                        output_file=generated.get("output_file"),
                        metadata=dict(generated.get("metadata", {})),
                    )
                )
                emitted += 1

        return records
