from copy import deepcopy
from numbers import Number
from typing import List, Set, Sequence
from abstract_domains.state import State
from abstract_domains.usage.used import UsedLattice, Used
from abstract_domains.generic_lattices import StoreLattice
from abstract_domains.usage.used_liststart import UsedListStartLattice
from core.expressions import Expression, VariableIdentifier, ListDisplay, Literal, Index, Slice
from math import inf

from core.expressions_tools import walk


class UsedStore(StoreLattice, State):
    def __init__(self, variables: List[VariableIdentifier]):
        super().__init__(variables, {int: UsedLattice, list: UsedListStartLattice})
        self._inside_print = False

    @property
    def inside_print(self):
        return self._inside_print

    @inside_print.setter
    def inside_print(self, flag: bool):
        self._inside_print = flag

    def __repr__(self):
        variables = ", ".join("{} -> {}".format(variable, value) for variable, value in self.variables.items())
        return variables

    def descend(self) -> 'UsedStore':
        for var in self.variables.values():
            var.descend()
        return self

    def combine(self, other: 'UsedStore') -> 'UsedStore':
        for var, used in self.variables.items():
            used.combine(other.variables[var])
        return self

    def _derive_list_display_usage_from_used_liststart(self, liststart, list_display):
        for index, e in enumerate(list_display.items):
            if liststart.used_at(index) in [Used.U, Used.S]:
                for identifier in e.ids():
                    self.variables[identifier].used = Used.U

    def _use(self, left: VariableIdentifier, right: Expression):
        if issubclass(left.typ, Number):
            if self.variables[left].used in [Used.U, Used.S]:
                for e in walk(right):
                    if isinstance(e, VariableIdentifier):
                        self.variables[e].used = Used.U
                    elif isinstance(e, Index):
                        if isinstance(e.index, Literal):
                            self.variables[e.target].set_used_at(e.index.val)
                        else:
                            raise NotImplementedError()
        elif issubclass(left.typ, Sequence):
            if isinstance(right, VariableIdentifier):
                self.variables[right].replace(deepcopy(self.variables[left]))
                self.variables[right].change_S_to_U()
            elif isinstance(right, ListDisplay):
                self._derive_list_display_usage_from_used_liststart(self.variables[left], right)
        else:
            raise NotImplementedError(f"Method _use not implemented for {self.variables[left].typ}!")
        return self

    def _kill(self, left: VariableIdentifier, right: Expression):
        if issubclass(left.typ, Number):
            if self.variables[left].used in [Used.U, Used.S]:
                if left in [v for v, u in self.variables.items() if v in right.ids()]:
                    self.variables[left].used = Used.U  # x is still used since it is used in assigned expression
                else:
                    self.variables[left].used = Used.O  # x is overwritten
        elif issubclass(left.typ, Sequence):
            # TODO this whole if is no longer correct when lists of lists are allowed, e.g. l = [a,2,l]
            if isinstance(right, VariableIdentifier):
                if right != left:  # if no self-assignemnt
                    self.variables[left].bottom()
            elif isinstance(right, ListDisplay):
                self.variables[left].change_SU_to_O()
        else:
            raise NotImplementedError(f"Method _kill not implemented for {self.variables[left].typ}!")
        return self

    def _access_variable(self, variable: VariableIdentifier) -> Set[Expression]:
        if self.inside_print:
            if issubclass(variable.typ, Number):
                self.variables[variable].used = Used.U
            elif issubclass(variable.typ, Sequence):
                self.variables[variable].suo[Used.U] = inf
                self.variables[variable].closure()
            else:
                raise NotImplementedError(f"Type {variable.typ} not yet supported!")
        return {variable}

    def _assign_variable(self, left: Expression, right: Expression) -> 'UsedStore':
        raise NotImplementedError("Variable assignment is not implemented!")

    def _assume(self, condition: Expression) -> 'UsedStore':
        used_vars = len(
            set([lat.used for lat in self.variables.values() if isinstance(lat, UsedLattice)]).intersection(
                [Used.U, Used.O])
        ) > 0
        used_lists = any(
            [lat.suo[Used.U] > 0 or lat.suo[Used.O] > 0 for lat in self.variables.values() if
             isinstance(lat, UsedListStartLattice)]
        )
        store_has_effect = used_vars or used_lists

        for e in walk(condition):
            if isinstance(e, VariableIdentifier):
                # update to U if exists a variable y in state that is either U or O (note that S is not enough)
                # or is set intersection, if checks if resulting list is empty
                if store_has_effect:
                    self.variables[e].used = Used.U
            elif isinstance(e, Index):
                if isinstance(e.index, Literal):
                    if store_has_effect:
                        self.variables[e.target].set_used_at(e.index.val)
                else:
                    raise NotImplementedError()

        return self

    def _evaluate_literal(self, literal: Expression) -> Set[Expression]:
        return {literal}

    def enter_loop(self):
        raise NotImplementedError("UsedStore does not support enter_loop")

    def exit_loop(self):
        raise NotImplementedError("UsedStore does not support exit_loop")

    def enter_if(self):
        raise NotImplementedError("UsedStore does not support enter_if")

    def exit_if(self):
        raise NotImplementedError("UsedStore does not support exit_if")

    def _substitute_variable(self, left: Expression, right: Expression) -> 'UsedStore':
        if isinstance(left, VariableIdentifier):
            self._use(left, right)._kill(left, right)
        else:
            raise NotImplementedError("Variable substitution for {} is not implemented!".format(left))
        return self
