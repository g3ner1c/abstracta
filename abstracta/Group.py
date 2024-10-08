"""Group implementation"""

from __future__ import annotations

import itertools
from typing import Callable, Self

from abstracta.Function import Function
from abstracta.Set import AlgSet


class GroupElem:
    """
    Group element definition

    This is mainly syntactic sugar, so you can write stuff like g * h
    instead of group.bin_op(g, h), or group(g, h).
    """

    def __init__(self, elem, group: Group):
        if not isinstance(group, Group):
            raise TypeError("group is not a Group")
        if elem not in group.Set:
            raise TypeError("elem is not an element of group")
        self.elem = elem
        self.group: Group = group

    def __str__(self) -> str:
        return str(self.elem)

    def __eq__(self, other) -> bool:
        """
        Two GroupElems are equal if they represent the same element,
        regardless of the Groups they belong to
        """

        if not isinstance(other, GroupElem):
            raise TypeError("other is not a GroupElem")
        return self.elem == other.elem

    def __ne__(self, other) -> bool:
        return not self == other

    def __hash__(self):
        return hash(self.elem)

    def __mul__(self, other) -> GroupElem:
        """
        If other is a group element, returns self * other.
        If other = n is an int, and self is in an abelian group, returns self**n
        """
        if self.group.is_abelian() and isinstance(other, (int)):
            return self**other

        if not isinstance(other, GroupElem):
            raise TypeError(
                "other must be a GroupElem, or an int " "(if self's group is abelian)"
            )
        try:
            return GroupElem(self.group.bin_op((self.elem, other.elem)), self.group)
        # This can return a TypeError in Funcion.__call__ if self and other
        # belong to different Groups. So we see if we can make sense of this
        # operation the other way around.
        except TypeError:
            return other.__rmul__(self)

    def __rmul__(self, other) -> GroupElem:
        """
        If other is a group element, returns other * self.
        If other = n is an int, and self is in an abelian group, returns self**n
        """
        if self.group.is_abelian() and isinstance(other, (int,)):
            return self**other

        if not isinstance(other, GroupElem):
            raise TypeError(
                "other must be a GroupElem, or an int " "(if self's group is abelian)"
            )

        return GroupElem(self.group.bin_op((other.elem, self.elem)), self.group)

    def __add__(self, other) -> GroupElem:
        """Returns self + other for Abelian groups"""
        if self.group.is_abelian():
            return self * other
        raise TypeError("not an element of an abelian group")

    def __pow__(self, n, modulo=None) -> GroupElem:
        """
        Returns self**n

        modulo is included as an argument to comply with the API, and ignored
        """
        if not isinstance(n, (int)):
            raise TypeError("n must be an int or a long")

        if n == 0:
            return self.group.e
        elif n < 0:
            return self.group.inverse(self) ** -n
        elif n % 2 == 1:
            return self * (self ** (n - 1))
        else:
            return (self * self) ** (n / 2)

    def __neg__(self) -> GroupElem:
        """Returns self ** -1 if self is in an abelian group"""
        if not self.group.is_abelian():
            raise TypeError("self must be in an abelian group")
        return self ** (-1)

    def __sub__(self, other) -> GroupElem:
        """Returns self * (other ** -1) if self is in an abelian group"""
        if not self.group.is_abelian():
            raise TypeError("self must be in an abelian group")
        return self * (other**-1)

    def order(self):
        """Returns the order of self in the Group"""
        return len(self.group.generate([self]))


class Group:
    """Group definition"""

    def __init__(self, G: AlgSet, bin_op: Function):
        """Create a group, checking group axioms"""

        # Test types
        if not isinstance(G, AlgSet):
            raise TypeError("G must be a set")
        if not isinstance(bin_op, Function):
            raise TypeError("bin_op must be a function")
        if bin_op.codomain != G:
            raise TypeError("binary operation must have codomain equal to G")
        if bin_op.domain != G * G:
            raise TypeError("binary operation must have domain equal to G * G")

        # Test associativity
        if not all(
            bin_op((a, bin_op((b, c)))) == bin_op((bin_op((a, b)), c))
            for a, b, c in itertools.product(G, G, G)
        ):
            raise ValueError("binary operation is not associative")

        # Find the identity
        found_id = False
        for e in G:
            if all(bin_op((e, a)) == a for a in G):
                found_id = True
                break
        if not found_id:
            raise ValueError("G doesn't have an identity")

        # Test for inverses
        for a in G:
            if not any(bin_op((a, b)) == e for b in G):
                raise ValueError("G doesn't have inverses")

        # At this point, we've verified that we have a Group.
        # Now determine if the Group is abelian:
        self.abelian: bool = all(
            bin_op((a, b)) == bin_op((b, a)) for a, b in itertools.product(G, G)
        )

        self.Set = G
        self.group_elems = AlgSet(GroupElem(g, self) for g in G)
        self.e = GroupElem(e, self)
        self.bin_op = bin_op

    def __iter__(self):
        """Iterate over the GroupElems in G, returning the identity first"""
        yield self.e
        for g in self.group_elems:
            if g != self.e:
                yield g

    def __contains__(self, item):
        return item in self.group_elems

    def __hash__(self):
        return hash(self.Set) ^ hash(self.bin_op)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Group):
            return False

        return id(self) == id(other) or (
            self.Set == other.Set and self.bin_op == other.bin_op
        )

    def __ne__(self, other) -> bool:
        return not self == other

    def __len__(self) -> int:
        return len(self.Set)

    def __str__(self) -> str:
        """Returns the Cayley table"""

        letters = "eabcdfghijklmnopqrstuvwxyz"
        if len(self) > len(letters):
            return "This group is too big to print a Cayley table"

        # connect letters to elements
        toletter = {}
        toelem = {}
        for letter, elem in zip(letters, self):
            toletter[elem] = letter
            toelem[letter] = elem
        letters = letters[: len(self)]

        # Display the mapping:
        result = "\n".join("%s: %s" % (l, toelem[l]) for l in letters) + "\n\n"

        # Make the graph
        head = "   | " + " | ".join(l for l in letters) + " |"
        border = (len(self) + 1) * "---+" + "\n"
        result += head + "\n" + border
        result += border.join(
            " %s | " % l
            + " | ".join(toletter[toelem[l] * toelem[l1]] for l1 in letters)
            + " |\n"
            for l in letters
        )
        result += border
        return result

    def is_abelian(self) -> bool:
        """Checks if the group is abelian"""
        return self.abelian

    def __le__(self, other) -> bool:
        """Checks if self is a subgroup of other"""
        if not isinstance(other, Group):
            raise TypeError("other must be a Group")
        return self.Set <= other.Set and all(
            self.bin_op((a, b)) == other.bin_op((a, b))
            for a, b in itertools.product(self.Set, self.Set)
        )

    def is_normal_subgroup(self, other) -> bool:
        """Checks if self is a normal subgroup of other"""
        return self <= other and all(
            AlgSet(g * h for h in self) == AlgSet(h * g for h in self) for g in other
        )

    def __div__(self, other) -> Group:
        """Returns the quotient group self / other"""
        if not other.is_normal_subgroup(self):
            raise ValueError("other must be a normal subgroup of self")
        G = AlgSet(AlgSet(self.bin_op((g, h)) for h in other.Set) for g in self.Set)

        def multiply_cosets(x):
            h = x[0].pick()
            return AlgSet(self.bin_op((h, g)) for g in x[1])

        return Group(G, Function(G * G, G, multiply_cosets))

    def inverse(self, g: GroupElem) -> GroupElem:
        """Returns the inverse of elem"""
        if g not in self.group_elems:
            raise TypeError("g isn't a GroupElem in the Group")
        for a in self:
            if g * a == self.e:
                return a
        raise RuntimeError("Didn't find an inverse for g")

    def __mul__(self, other) -> Group:
        """Returns the cartesian product of the two groups"""
        if not isinstance(other, Group):
            raise TypeError("other must be a group")
        bin_op = Function(
            (self.Set * other.Set) * (self.Set * other.Set),
            (self.Set * other.Set),
            lambda x: (
                self.bin_op((x[0][0], x[1][0])),
                other.bin_op((x[0][1], x[1][1])),
            ),
        )

        return Group(self.Set * other.Set, bin_op)

    def generate(self, elems) -> Group:
        """
        Returns the subgroup of self generated by GroupElems elems

        If any of the items aren't already GroupElems, we will try to convert
        them to GroupElems before continuing.

        elems must be iterable
        """

        elems = AlgSet(
            g if isinstance(g, GroupElem) else GroupElem(g, self) for g in elems
        )

        if not elems <= self.group_elems:
            raise ValueError("elems must be a subset of self.group_elems")
        if len(elems) == 0:
            raise ValueError("elems must have at least one element")

        oldG = elems
        while True:
            newG = oldG | AlgSet(a * b for a, b in itertools.product(oldG, oldG))
            if oldG == newG:
                break
            else:
                oldG = newG
        oldG = AlgSet(g.elem for g in oldG)

        return Group(oldG, self.bin_op.new_domains(oldG * oldG, oldG))

    def is_cyclic(self) -> bool:
        """Checks if self is a cyclic Group"""
        return any(g.order() == len(self) for g in self)

    def subgroups(self):  # read up on this
        """Returns the Set of self's subgroups"""

        old_sgs = AlgSet([self.generate([self.e])])
        while True:
            new_sgs = old_sgs | AlgSet(
                self.generate(list(sg.group_elems) + [g])
                for sg in old_sgs
                for g in self
                if g not in sg.group_elems
            )
            if new_sgs == old_sgs:
                break
            else:
                old_sgs = new_sgs

        return old_sgs

    def generators(self) -> list[GroupElem]:  # read up on this
        """
        Returns a list of GroupElems that generate self, with length
        at most log_2(len(self)) + 1
        """

        result = [self.e.elem]  # initialize generator list with identity
        H = self.generate(result)  # initialize trivial subgroup

        while len(H) < len(self):  # group has not been fully generated
            result.append(
                (self.Set - H.Set).pick()
            )  # add an arbitrary element that has not been generated in H
            H = self.generate(result)  # repeat

        # The identity is always a redundant generator in nontrivial Groups, remove it
        if len(self) != 1:
            result = result[1:]

        return [GroupElem(g, self) for g in result]

    def find_isomorphism(self, other):  # read up on this
        """
        Returns an isomorphic GroupHomomorphism between self and other,
        or None if self and other are not isomorphic

        Uses Tarjan's algorithm, running in O(n^(log n + O(1))) time, but
        runs a lot faster than that if the group has a small generating set.
        """
        if not isinstance(other, Group):
            raise TypeError("other must be a Group")

        if len(self) != len(other) or self.is_abelian() != other.is_abelian():
            return None

        # Try to match the generators of self with some subset of other
        A = self.generators()
        for B in itertools.permutations(other, len(A)):

            func = dict(zip(A, B))  # the mapping
            counterexample = False
            while not counterexample:

                # Loop through the mapped elements so far, trying to extend the
                # mapping or else find a counterexample
                noobs = {}
                for g, h in itertools.product(func, func):
                    if g * h in func:
                        if func[g] * func[h] != func[g * h]:
                            counterexample = True
                            break
                    else:
                        noobs[g * h] = func[g] * func[h]

                # If we've mapped all the elements of self, then it's a
                # homomorphism provided we haven't seen any counterexamples.
                if len(func) == len(self):
                    break

                # Make sure there aren't any collisions before updating
                imagelen = len(set(noobs.values()) | set(func.values()))
                if imagelen != len(noobs) + len(func):
                    counterexample = True
                func.update(noobs)

            if not counterexample:
                return GroupHomomorphism(self, other, lambda x: func[x])

        return None

    def is_isomorphic(self, other):
        """Checks if self and other are isomorphic"""
        return bool(self.find_isomorphism(other))


class GroupHomomorphism(Function):  # maybe make this a polymorphism
    """
        The definition of a Group Homomorphism
    20
        A GroupHomomorphism is a Function between Groups that obeys the group
        homomorphism axioms.
    """

    def __init__(self, domain: Group, codomain: Group, function):
        """Check types and the homomorphism axioms; records the two groups"""

        if not isinstance(domain, Group):
            raise TypeError("domain must be a Group")
        if not isinstance(codomain, Group):
            raise TypeError("codomain must be a Group")
        if not all(function(elem) in codomain for elem in domain):
            raise TypeError("Function returns some value outside of codomain")

        if not all(
            function(a * b) == function(a) * function(b)
            for a, b in itertools.product(domain, domain)
        ):
            raise ValueError("function doesn't satisfy the homomorphism axioms")

        self.domain: Group = domain
        self.codomain: Group = codomain
        self.function = function

    def kernel(self) -> Group:
        """Returns the kernel of the homomorphism as a Group object"""
        G = AlgSet(g.elem for g in self.domain if self(g) == self.codomain.e)
        return Group(G, self.domain.bin_op.new_domains(G * G, G))

    def image(self) -> Group:
        """Returns the image of the homomorphism as a Group object"""
        G = AlgSet(g.elem for g in self._image())
        return Group(G, self.codomain.bin_op.new_domains(G * G, G))

    def is_isomorphism(self) -> bool:  # check definition
        return self.is_bijective()


def Zn(n) -> Group:
    """Returns the cylic group of order n"""
    G = AlgSet(range(n))
    bin_op = Function(G * G, G, lambda x: (x[0] + x[1]) % n)
    return Group(G, bin_op)


def Sn(n) -> Group:
    """Returns the symmetric group of order n!"""
    G = AlgSet(g for g in itertools.permutations(range(n)))
    bin_op = Function(G * G, G, lambda x: tuple(x[0][j] for j in x[1]))
    return Group(G, bin_op)


def Dn(n) -> Group:
    """Returns the dihedral group of order 2n"""
    G = AlgSet("%s%d" % (l, x) for l in "RS" for x in range(n))

    def multiply_symmetries(x):
        l1, l2 = x[0][0], x[1][0]
        x1, x2 = int(x[0][1:]), int(x[1][1:])
        if l1 == "R":
            if l2 == "R":
                return "R%d" % ((x1 + x2) % n)
            else:
                return "S%d" % ((x1 + x2) % n)
        else:
            if l2 == "R":
                return "S%d" % ((x1 - x2) % n)
            else:
                return "R%d" % ((x1 - x2) % n)

    return Group(G, Function(G * G, G, multiply_symmetries))
