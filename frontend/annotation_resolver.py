import re


class AnnotationResolver:
    """Resolver for type annotations in functions"""
    def __init__(self, z3_types):
        self.z3_types = z3_types
        self.primitives = {
            "object": z3_types.object,
            "int": z3_types.int,
            "bool": z3_types.bool,
            "float": z3_types.float,
            "complex": z3_types.complex,
            "str": z3_types.string,
            "bytes": z3_types.bytes,
            "None": z3_types.none
        }
        self.complex_regex = {
            "List\[(.+)\]": z3_types.list,
            "Dict\[(.+), (.+)\]": z3_types.dict,
            "Set\[(.+)\]": z3_types.set,
            "Type\[(.+)\]": z3_types.type,
        }

        # Add functions regex:
        # funcs[0] --> Callable[[], (.+)]
        # funcs[1] --> Callable[[(.*)], (.+)]
        # funcs[2] --> Callable[[(.*), (.*)], (.+)]
        # ..etc.
        for i in range(len(z3_types.funcs)):
            args_groups = ["(.+)"] * i
            func_regex = "Callable\[\[{}\], (.+)\]".format(", ".join(args_groups))
            self.complex_regex[func_regex] = z3_types.funcs[i]

    def resolve(self, annotation):
        """Resolve the type annotation with the following grammar:
        
        t = object | int | bool | float | complex | str | bytes | None
            | List[t]
            | Dict[t, t]
            | Set[t]
            | Callable[[t*], t]
            | Type[t]
        """
        if annotation in self.primitives:  # check if it's primitive type
            return self.primitives[annotation]

        # check if it's complex type
        for regex in self.complex_regex:
            match = re.match(regex, annotation)
            if match:
                resolved_type = self.complex_regex[regex]
                args = []
                for arg_annotation in match.groups():
                    args.append(self.resolve(arg_annotation))
                return resolved_type(*args)

        # check if it's user defined type
        if annotation in self.z3_types.all_types:
            return getattr(self.z3_types.type_sort, "class_{}".format(annotation))
        raise ValueError("Invalid type annotation: {}.".format(annotation))
