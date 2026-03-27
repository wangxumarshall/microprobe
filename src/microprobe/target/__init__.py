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
""":mod:`microprobe.target` package

A target is defined by three components. The architecture definition
(see :mod:`~.isa` subpackage), the microarchitecture definition
(see :mod:`~.uarch` subpackage) and the environment definition
(see :mod:`~.env` subpackage). These three elements define the properties
of the target which might be queried during the code generation in order
to drive the code generation.

The main elements of this package are the following:

- :func:`~.import_definition` function provides support for importing target
  definitions.
- :class:`~.Definition` objects encapsulate the required information to be
  able to import architecture, microarchitecture or environment definitions.
- :class:`~.Target` objects are in charge of providing a generic API to query
  all kind of target properties. This is the main object that is used by other
  modules and packages of microprobe to query target information (e.g.
  instructions, registers, functional units, etc.).
"""

# Futures
from __future__ import absolute_import, annotations

# Built-in modules
import copy
import itertools
import os
from typing import TYPE_CHECKING, Tuple

# Third party modules

# Own modules
from microprobe.exceptions import MicroprobeError, \
    MicroprobeTargetDefinitionError
from microprobe.target.env import GenericEnvironment, \
    find_env_definitions, import_env_definition
from microprobe.target.isa import find_isa_definitions, import_isa_definition
from microprobe.target.uarch import find_microarchitecture_definitions, \
    import_microarchitecture_definition
from microprobe.utils.logger import get_logger
from microprobe.utils.misc import Pickable

# Local modules

# Type hinting
if TYPE_CHECKING:
    from microprobe.target.env import Environment
    from microprobe.target.isa import ISA
    from microprobe.target.uarch import Microarchitecture
    from microprobe.code.wrapper import Wrapper

# Constants
LOG = get_logger(__name__)
__all__ = [
    "import_definition",
    # "import_policies",
    "Target",
    "Definition"
]

_DEFINITION_TUPLE_ALIASES = {
    # Legacy local ARM64 tuple used throughout the in-tree tests and notes.
    "armv8-common-cortex-a53-aarch64_linux_gcc":
    "armv8_common-armv8_common-aarch64_linux_gcc",
    "armv8-common-cortex-a53-aarch64_baremetal":
    "armv8_common-armv8_common-aarch64_baremetal",
}


# Functions
def import_definition(definition_tuple: str
                      | Tuple[Definition, Definition, Definition]):
    """Return the target corresponding the to the given *definition_tuple*.

    Return the target object corresponding the to the given
    *definition_tuple*. The *definition_tuple* is a string of the form
    ``<architecture_name>-<uarch_name>-<environment_name>`` that defines the
    target. This function uses the search paths provided in the configuration
    to look for the definitions to import.

    :param definition_tuple: Target definition string
    :type definition_tuple: :class:`~.str`
    :return: The target object corresponding to the given *definition_tuple*
    :rtype: :class:`~.Target`
    :raise microprobe.exceptions.MicroprobeTargetDefinitionError: if something
        is wrong during the import
    """
    LOG.debug("Start importing definition tuple")

    if isinstance(definition_tuple, str):
        definition_tuple = _parse_definition_tuple(definition_tuple)

    # Type hinting needs some help here :)
    assert not isinstance(definition_tuple, str)

    isa_def, uarch_def, env_def = definition_tuple
    isa = import_isa_definition(os.path.dirname(isa_def.filename))
    env = import_env_definition(env_def.filename,
                                isa,
                                definition_name=env_def.name)
    uarch = import_microarchitecture_definition(
        os.path.dirname(uarch_def.filename))

    target = Target(isa, uarch=uarch, env=env)
    LOG.info("Target '%s-%s-%s' imported", isa_def.name, uarch_def.name,
             env_def.name)
    LOG.debug("End importing definition tuple")
    return target


def _parse_definition_tuple(definition_tuple: str):
    """Return the target definitions corresponding to the *definition_tuple*.

    Return the target definitions corresponding to the *definition_tuple*.
    Check the *definition_tuple* format, and for each element (architecture,
    microarchitecture and environment) looks for the if there is a definition
    present in the current defined definition paths. It returns a tuple with
    the three corresponding definitions.

    :param definition_tuple: Target definition string
    :type definition_tuple: :class:`~.str`
    :return: Tuple of target definitions
    :rtype: :func:`tuple` of :class:`~.Definition`
    :raise microprobe.exceptions.MicroprobeTargetDefinitionError: if something
        if the *definition_tuple* format is wrong or if the definition
        specified is not found
    """

    definition_tuple = _DEFINITION_TUPLE_ALIASES.get(
        definition_tuple, definition_tuple
    )

    isa_defs = find_isa_definitions()
    uarch_defs = find_microarchitecture_definitions()
    env_defs = find_env_definitions()

    env_def = _match_definition_suffix(definition_tuple, env_defs, "Environment")
    prefix = definition_tuple[:-(len(env_def.name) + 1)]

    isa_def = _match_definition_prefix(prefix, isa_defs, "ISA")
    architecture_name = prefix[len(isa_def.name) + 1:]
    architecture_def = _match_definition_name(
        architecture_name, uarch_defs, "Microarchitecture"
    )

    return (isa_def, architecture_def, env_def)


def _normalize_definition_name(name: str) -> str:
    return name.replace("-", "_")


def _match_definition_name(definition_name: str, definitions, kind: str):
    candidates = [definition for definition in definitions if definition.name == definition_name]
    if candidates:
        return candidates[-1]

    normalized = _normalize_definition_name(definition_name)
    candidates = [
        definition
        for definition in definitions
        if _normalize_definition_name(definition.name) == normalized
    ]
    if candidates:
        return candidates[-1]

    raise MicroprobeTargetDefinitionError(
        "%s '%s' not available" % (kind, definition_name)
    )


def _match_definition_suffix(definition_tuple: str, definitions, kind: str):
    ordered = sorted(definitions, key=lambda definition: len(definition.name), reverse=True)
    for definition in ordered:
        if definition_tuple == definition.name:
            return definition
        if definition_tuple.endswith("-%s" % definition.name):
            return definition
        normalized_tuple = _normalize_definition_name(definition_tuple)
        if normalized_tuple.endswith("-%s" % _normalize_definition_name(definition.name)):
            return definition

    raise MicroprobeTargetDefinitionError(
        "%s not available in target tuple '%s'" % (kind, definition_tuple)
    )


def _match_definition_prefix(definition_tuple: str, definitions, kind: str):
    ordered = sorted(definitions, key=lambda definition: len(definition.name), reverse=True)
    normalized_tuple = _normalize_definition_name(definition_tuple)
    for definition in ordered:
        if definition_tuple == definition.name:
            return definition
        if definition_tuple.startswith("%s-" % definition.name):
            return definition
        normalized_name = _normalize_definition_name(definition.name)
        if normalized_tuple.startswith("%s-" % normalized_name):
            return definition

    raise MicroprobeTargetDefinitionError(
        "%s not available in target tuple '%s'" % (kind, definition_tuple)
    )


# def import_policies(target_name):
#    """Return the dictionary of policies for the *target_name*."""
#
#    paths = MICROPROBE_RC["default_paths"]
#    policies = RejectingDict()
#
#    for policy_file in findfiles(paths, "^.*.py$"):
#
#        LOG.debug("Looking for policies in '%s'", policy_file)
#
#        try:
#
#            name = get_attr_from_module("NAME", policy_file)
#            description = get_attr_from_module("DESCRIPTION", policy_file)
#            targets = get_attr_from_module("SUPPORTED_TARGETS", policy_file)
#            policy = get_attr_from_module("policy", policy_file)
#            extra = get_dict_from_module(policy_file)
#
#            LOG.debug("Policy '%s' found!", name)
#
#            if target_name in targets:
#
#                LOG.debug("Policy '%s' valid!", name)
#                policies[name] = Policy(name, description, policy,
#                                        targets, extra, policy_file)
#
#        except MicroprobeImportDefinitionError:
#            LOG.debug("Not a policy module")
#            continue
#
#        except MicroprobeDuplicatedValueError:
#            raise MicroprobePolicyError(
#                "Policy '%s' in '%s' is duplicated" % (name, policy_file)
#            )
#
#    return policies


# Classes
class Definition:
    """Class to represent a target element definition.

    A target element definition could be the definition of the architecture,
    the microarchitecture or the environment. In all three cases a definition
    is composed by the definition name, the filename (where in the file system
    the definition is located) and the description.
    """

    # Class constant used for nice string formmating
    _field1 = 18
    _field2 = 25
    _field3 = 78 - _field1 - _field2
    _fmt_str_ = "Name:'%%%ds', Description:'%%%ds', File:'%%%ds'" % (
        _field1, _field2, _field3)
    _cmp_attributes = ["name", "description", "filename"]

    def __init__(self, filename: str, name: str, description: str):
        """Create a Definition object.

        :param filename: Filename where the definition is placed
        :type filename: :class:`~.str`
        :param name: Name of the definition
        :type name: :class:`~.str`
        :param description: Description of the definition
        :type description: :class:`~.str`
        :return: Definition instance
        :rtype: :class:`~.Definition`
        """
        self._file = filename
        self._name = name
        self._description = description

    @property
    def description(self):
        """Description of the definition (:class:`~.str`)."""
        return self._description

    @property
    def filename(self):
        """Filename of the definition (:class:`~.str`)."""
        return self._file

    @property
    def name(self):
        """Name of the definition (:class:`~.str`)."""
        return self._name

    def __str__(self):
        """x.__str__() <==> str(x)."""
        return self._fmt_str_ % (self._name, self._description, self._file)

    def _check_cmp(self, other):
        if not isinstance(other, self.__class__):
            raise NotImplementedError("%s != %s" %
                                      (other.__class__, self.__class__))

    def __eq__(self, other):
        """x.__eq__(y) <==> x==y"""
        self._check_cmp(other)
        for attr in self._cmp_attributes:
            if not getattr(self, attr) == getattr(other, attr):
                return False
        return True

    def __ne__(self, other):
        """x.__ne__(y) <==> x!=y"""
        self._check_cmp(other)
        for attr in self._cmp_attributes:
            if not getattr(self, attr) == getattr(other, attr):
                return True
        return False

    def __lt__(self, other):
        """x.__lt__(y) <==> x<y"""
        self._check_cmp(other)
        for attr in self._cmp_attributes:
            if getattr(self, attr) < getattr(other, attr):
                return True
            elif getattr(self, attr) > getattr(other, attr):
                return False
        return False

    def __gt__(self, other):
        """x.__gt__(y) <==> x>y"""
        self._check_cmp(other)
        for attr in self._cmp_attributes:
            if getattr(self, attr) > getattr(other, attr):
                return True
            elif getattr(self, attr) < getattr(other, attr):
                return False
        return False

    def __le__(self, other):
        """x.__le__(y) <==> x<=y"""
        self._check_cmp(other)
        for attr in self._cmp_attributes:
            if getattr(self, attr) <= getattr(other, attr):
                continue
            else:
                return False
        return True

    def __ge__(self, other):
        """x.__ge__(y) <==> x>=y"""
        self._check_cmp(other)
        for attr in self._cmp_attributes:
            if getattr(self, attr) >= getattr(other, attr):
                return True
            else:
                return False
        return False


class Target(Pickable):
    """Class to represent a code generation target.

    A target is defined by the architecture, the microarchitecture
    implementation and the generation environment.
    The Target object provides a common interface to all the
    architecture/microarchitecture/environment specific methods using a
    facade software design pattern.
    Therefore, all the references to target related properties should go
    through this object interface in order to minimize the coupling with the
    other modules (code generation, design space exploration, ...).
    """

    def __init__(self,
                 isa: ISA,
                 env: Environment | None = None,
                 uarch: Microarchitecture | None = None):
        """Create a Target object.

        :param isa: Architecture (i.e. Instruction Set Architecture)
        :type isa: :class:`~.ISA`
        :param env: Environment (default: None)
        :type env: :class:`~.Environment`
        :param uarch: Microarchitecture (default: None)
        :type uarch: :class:`~.Microarchitecture`
        :return: Target instance
        :rtype: :class:`~.Target`
        """
        self._uarch: Microarchitecture | None = None
        self._env: Environment | None = None
        self._policies = None
        self._wrapper: Wrapper | None = None

        self.set_isa(isa)

        if uarch is not None:
            self.set_uarch(uarch)
            self.microarchitecture.add_properties_to_isa(self.isa.instructions)

        if env is not None:
            self.set_env(env)
        else:
            self.set_env(
                GenericEnvironment("Default", "Empty environment", self.isa))

    @property
    def name(self):
        """Name of the Target (:class:`~.str`)."""
        name = self._isa.name
        if self._uarch is not None:
            name += "-" + self._uarch.name
        if self._env is not None:
            name += "-" + self._env.name
        return name

    @property
    def description(self):
        """Description of the Target (:class:`~.str`)."""
        description = []
        description.append("Target ISA: %s" % self.isa.name)
        description.append("ISA Description: %s" % self.isa.description)
        if self.microarchitecture is not None:
            description.append("Target Micro-architecture: %s" %
                               self.microarchitecture.name)
            description.append("Micro-architecture Description: %s" %
                               self.microarchitecture.description)
        else:
            description.append("Target Micro-architecture: Not defined")
            description.append("Micro-architecture Description: Not defined")
        description.append("Target Environment: %s" % self.environment.name)
        description.append("Environment description: %s" %
                           self.environment.description)
        return "\n".join(description)

    @property
    def environment(self):
        """Environment of the Target (:class:`~.Environment`)."""
        return self._env

    @property
    def isa(self):
        """Architecture of the Target (:class:`~.ISA`)."""
        return self._isa

    @property
    def microarchitecture(self):
        """Microarchitecture of the Target (:class:`~.Microarchitecture`)."""
        return self._uarch

    @property
    def reserved_registers(self):
        """Reserved registers of the Target (:class:`~.list` of
        :class:`~.Register`)."""
        return self.environment.environment_reserved_registers + \
            self.isa.scratch_registers

    @property
    def wrapper(self):
        """Wrapper of the Target (:class:`~.Wrapper`)."""
        return self._wrapper

    def full_report(self):
        """Return a long description of the Target.

        :rtype: :class:`~.str`
        """
        rstr = self.isa.full_report() + '\n'
        if self.microarchitecture is not None:
            rstr += self.microarchitecture.full_report() + '\n'
        rstr += self.environment.full_report() + '\n'
        return rstr

    def property_isa_map(self, prop_name):
        """Generate property to isa map.

        Return a dictionary mapping values of the property *prop_name* to
        the list of :class:`~.InstructionType` that have that property value.

        :param prop_name: Property name
        :type prop_name: :class:`~.str`
        :return: Dictionary mapping value properties to instruction types
        :rtype: :class:`~.dict` mapping property values to :class:`~.list` of
                :class:`~.InstructionType`
        :raise microprobe.exceptions.MicroprobeTargetDefinitionError: if the
            property is not found
        """
        prop_map = {}

        for instr in self.isa.instructions.values():

            try:
                value = getattr(instr, prop_name)
            except AttributeError:
                raise MicroprobeTargetDefinitionError(
                    "Property '%s' for instruction not found" % prop_name)

            if not isinstance(value, list):
                values = [value]
            else:
                values = value

            for value in values:

                if value not in prop_map:
                    prop_map[value] = []

                prop_map[value].append(instr)

        for key in prop_map.keys():
            prop_map[key] = set(prop_map[key])

        return prop_map

    def set_env(self, env: Environment):
        """Set the environment of the Target.

        :param env: Execution environment definition
        :type env: :class:`~.Environment`
        """
        self._env = copy.deepcopy(env)
        self._env.set_target(self)

    def set_isa(self, isa: ISA):
        """Set the ISA of the Target.

        :param isa: Architecture (i.e. ISA)
        :type isa: :class:`~.ISA`
        """
        self._isa = copy.deepcopy(isa)
        self._isa.set_target(self)

    def set_uarch(self, uarch: Microarchitecture):
        """Set the microarchitecture of the Target.

        :param uarch: Microarchitecture
        :type uarch: :class:`~.Microarchitecture`
        """
        self._uarch = uarch
        self._uarch.set_target(self)

    # TODO: remove this interface once the code generation back-end is fixed
    def set_wrapper(self, wrapper: Wrapper):
        """Set the wrapper of the Target.

        :param wrapper: Wrapper
        :type wrapper: :class:`~.Wrapper`
        """
        self._wrapper = wrapper

    # TODO: Remove facade pattern to allow type hints to propagate
    def __getattr__(self, name):
        """Facade design pattern implementation.

        This is where we implement the facade design pattern. Whenever an
        attribute is not defined by the Target object itself, it is searched
        if it is defined by one of the three elements composing the target.

        :param name: Attribute name
        :type name: :class:`~.str`
        :return: Attribute value
        :rtype: Type of the value of the attribute requested
        :raise microprobe.exceptions.MicroprobeError: if attribute is defined
            in multiple objects
        :raise AttributeError: if attribute is not found in the class
               or any of the facade classes
        """
        if name in ["description", "name"]:
            return self.__getattribute__(name)

        attrs = []
        if self._isa is not None:
            try:
                attrs.append(self._isa.__getattribute__(name))
            except AttributeError:
                pass

        if self._uarch is not None:
            try:
                attrs.append(self._uarch.__getattribute__(name))
            except AttributeError:
                pass

        if self._env is not None:
            try:
                attrs.append(self._env.__getattribute__(name))
            except AttributeError:
                pass

        if len(attrs) == 1:
            return attrs[0]
        elif len(attrs) > 1:
            if all([isinstance(attr, list) for attr in attrs]):
                return list(itertools.chain.from_iterable(attrs))
            else:
                raise MicroprobeError("Attribute defined in multiple objects")
        else:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.__class__.__name__, name))
