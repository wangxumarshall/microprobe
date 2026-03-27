# Copyright 2011-2023 IBM Corporation
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
""":mod:`microprobe.utils.typeguard_decorator` module

"""

# Futures


# Built-in modules
import sys
from typing import Any


# Third party modules
typeguard = None
if "unittest" in sys.modules:
    # running in testsuite, enable runtime type checking
    try:
        import typeguard
    except ImportError:  # pragma: no cover - optional dependency
        typeguard = None


# Constants
__all__ = ["typeguard_testsuite"]


# Functions
def typeguard_testsuite(dec: Any) -> Any:
    """Only perform runtime type checking when running testsuite"""
    if "unittest" in sys.modules and typeguard is not None:
        return typeguard.typechecked(dec)
    return dec
