from islpy._isl import *
from islpy.version import *


def _add_functionality():
    import islpy._isl as _isl

    _CHECK_DIM_TYPES = [
            dim_type.in_, dim_type.param, dim_type.set, dim_type.cst, dim_type.div]

    ALL_CLASSES = [getattr(_isl, cls) for cls in dir(_isl) if cls[0].isupper()]

    # {{{ printing

    def generic_repr(self):
        prn = Printer.to_str(self.get_ctx())
        getattr(prn, "print_"+self._base_name)(self)
        return prn.get_str()

    for cls in ALL_CLASSES:
        if hasattr(Printer, "print_"+cls._base_name):
            cls.__repr__ = generic_repr

    # }}}

    # {{{ Space

    def space_get_var_dict(self, dimtype=None):
        """Return a dictionary mapping variable names to tuples of (:class:`dim_type`, index).

        :param dimtype: None to get all variables, otherwise
            one of :class:`dim_type`.
        """
        result = {}

        def set_dim_name(name, tp, idx):
            if name in result:
                raise RuntimeError("non-unique var name '%s' encountered" % name)
            result[name] = tp, idx

        if dimtype is None:
            types = _CHECK_DIM_TYPES
        else:
            types = [dimtype]

        for tp in types:
            for i in range(self.dim(tp)):
                name = self.get_dim_name(tp, i)
                if name is not None:
                    set_dim_name(name, tp, i)

        return result

    def space_create_from_names(ctx, set=None, in_=None, out=None, params=[]):
        """Create a :class:`Space` from lists of variable names.

        :param set_`: names of `set`-type variables.
        :param in_`: names of `in`-type variables.
        :param out`: names of `out`-type variables.
        :param params`: names of parameter-type variables.
        """
        dt = dim_type

        if set is not None:
            if in_ is not None or out is not None:
                raise RuntimeError("must pass only one of set / (in_,out)")

            result = Space.set_alloc(ctx, nparam=len(params),
                    dim=len(set))

            for i, name in enumerate(set):
                result = result.set_dim_name(dt.set, i, name)

        elif in_ is not None and out is not None:
            if set is not None:
                raise RuntimeError("must pass only one of set / (in_,out)")

            result = Space.alloc(ctx, nparam=len(params),
                    n_in=len(in_), n_out=len(out))

            for i, name in enumerate(in_):
                result = result.set_dim_name(dt.in_, i, name)

            for i, name in enumerate(out):
                result = result.set_dim_name(dt.out, i, name)
        else:
            raise RuntimeError("invalid parameter combination")

        for i, name in enumerate(params):
            result = result.set_dim_name(dt.param, i, name)

        return result

    Space.create_from_names = staticmethod(space_create_from_names)
    Space.get_var_dict = space_get_var_dict

    # }}}

    # {{{ coefficient wrangling

    def obj_set_coefficients(self, dim_tp, args):
        """
        :param dim_tp: :class:`dim_type`
        :param args: :class:`list` of coefficients, for indices `0..len(args)-1`.

        .. versionchanged:: 2011.3
            New for :class:`Aff`, :class:`Div`.
        """
        for i, coeff in enumerate(args):
            self = self.set_coefficient(dim_tp, i, coeff)

        return self

    def obj_set_coefficients_by_name(self, iterable, name_to_dim=None):
        """Set the coefficients and the constant.

        :param iterable: a :class:`dict` or iterable of :class:`tuple`
            instances mapping variable names to their coefficients.
            The constant is set to the value of the key '1'.

        .. versionchanged:: 2011.3
            New for :class:`Aff`, :class:`Div`.
        """
        try:
            iterable = iterable.iteritems()
        except AttributeError:
            pass

        if name_to_dim is None:
            name_to_dim = self.get_space().get_var_dict()

        for name, coeff in iterable:
            if name == 1:
                self = self.set_constant(coeff)
            else:
                tp, idx = name_to_dim[name]
                self = self.set_coefficient(tp, idx, coeff)

        return self

    def obj_get_coefficients_by_name(self, dimtype=None, dim_to_name=None):
        """Return a dictionary mapping variable names to coefficients.

        :param dimtype: None to get all variables, otherwise
            one of :class:`dim_type`.

        .. versionchanged:: 2011.3
            New for :class:`Aff`, :class:`Div`.
        """
        if dimtype is None:
            types = _CHECK_DIM_TYPES
        else:
            types = [dimtype]

        result = {}
        for tp in types:
            for i in range(self.dim(tp)):
                coeff = self.get_coefficient(tp, i)
                if coeff:
                    if dim_to_name is None:
                        name = self.get_dim_name(tp, i)
                    else:
                        name = dim_to_name[(tp, i)]

                    result[name] = coeff

        const = self.get_constant()
        if const:
            result[1] = const

        return result

    for coeff_class in [Constraint, Aff, Div]:
        coeff_class.set_coefficients = obj_set_coefficients
        coeff_class.set_coefficients_by_name = obj_set_coefficients_by_name
        coeff_class.get_coefficients_by_name = obj_get_coefficients_by_name

    # }}}

    # {{{ Constraint

    def eq_from_names(space, coefficients={}):
        """Create a constraint `const + coeff_1*var_1 +... == 0`.

        :param space: :class:`Space`
        :param coefficients: a :class:`dict` or iterable of :class:`tuple`
            instances mapping variable names to their coefficients
            The constant is set to the value of the key '1'.

        .. versionchanged:: 2011.3
            Eliminated the separate *const* parameter.
        """
        c = Constraint.equality_alloc(space)
        return c.set_coefficients_by_name(coefficients)

    def ineq_from_names(space, coefficients={}):
        """Create a constraint `const + coeff_1*var_1 +... >= 0`.

        :param space: :class:`Space`
        :param coefficients: a :class:`dict` or iterable of :class:`tuple` 
            instances mapping variable names to their coefficients
            The constant is set to the value of the key '1'.

        .. versionchanged:: 2011.3
            Eliminated the separate *const* parameter.
        """
        c = Constraint.inequality_alloc(space)
        return c.set_coefficients_by_name(coefficients)

    Constraint.eq_from_names = staticmethod(eq_from_names)
    Constraint.ineq_from_names = staticmethod(ineq_from_names)

    # }}}

    def basic_obj_get_constraints(self):
        """Get a list of constraints."""
        result = []
        self.foreach_constraint(result.append)
        return result

    # {{{ BasicSet

    def basic_set_as_set(self):
        """Return self as a :class:`Set`."""
        return Set.from_basic_set(self)


    BasicSet.as_set = basic_set_as_set
    BasicSet.get_constraints = basic_obj_get_constraints

    # }}}

    # {{{ BasicMap

    def basic_map_as_map(self):
        """Return *self* as a :class:`Map`."""
        return Map.from_basic_map(self)

    BasicMap.as_map = basic_map_as_map
    BasicMap.get_constraints = basic_obj_get_constraints

    # }}}

    # {{{ Set

    def set_get_basic_sets(self):
        """Get the list of :class:`BasicSet` instances in this :class:`Set`."""
        result = []
        self.foreach_basic_set(result.append)
        return result

    Set.get_basic_sets = set_get_basic_sets

    # }}}

    # {{{ Map

    def map_get_basic_maps(self):
        """Get the list of :class:`BasicMap` instances in this :class:`Map`."""
        result = []
        self.foreach_basic_map(result.append)
        return result

    Map.get_basic_maps = map_get_basic_maps

    # }}}

    # {{{ add automatic upcasts

    class UpcastWrapper(object):
        def __init__(self, method, upcast):
            self.method = method
            self.upcast = upcast

    def add_upcasts(basic_class, special_class, upcast_method):
        from functools import update_wrapper

        from inspect import ismethod
        for method_name in dir(special_class):
            if hasattr(basic_class, method_name):
                continue

            method = getattr(special_class, method_name)

            if ismethod(method):
                def make_wrapper(method, upcast):
                    # this function provides a scope in which method and upcast
                    # are not changed

                    def wrapper(basic_instance, *args, **kwargs):
                        special_instance = upcast(basic_instance)
                        return method(special_instance, *args, **kwargs)

                    return wrapper

                wrapper = make_wrapper(method, upcast_method)
                setattr(basic_class, method_name, update_wrapper(wrapper, method))

    for args_triple in [
            (BasicSet, Set, BasicSet.as_set),
            (BasicMap, Map, BasicMap.as_map),
            ]:
        add_upcasts(*args_triple)

    # }}}

    # {{{ project_out_except

    def obj_project_out_except(obj, names, types):
        """
        :param types: list of :class:`dim_type` determining
            the types of axes to project out
        :param names: names of axes matching the above which
            should be left alone by the projection

        .. versionadded:: 2011.3
        """

        for tp in types:
            while True:
                space = obj.get_space()
                var_dict = space.get_var_dict(tp)

                all_indices = set(xrange(space.size(tp)))
                leftover_indices = set(var_dict[name][1] for name in names
                        if name in var_dict)
                project_indices = all_indices-leftover_indices
                if not project_indices:
                    break

                min_index = min(project_indices)
                count = 1
                while min_index+count in project_indices:
                    count += 1

                obj = obj.project_out(tp, min_index, count)

        return obj
    # }}}

    # {{{ remove_divs_of_dim_type

    def obj_remove_divs_of_dim_type(self, type):
        """
        .. versionadded:: 2011.3
        """
        result = self.remove_divs_involving_dims(
            type, 0, self.get_space().size(type))

        basic_objs = None
        if isinstance(self, BasicSet):
            basic_objs = result.get_basic_sets()
        elif isinstance(self, BasicMap):
            basic_objs = result.get_basic_maps()

        if basic_objs is not None and len(basic_objs) == 1:
            return basic_objs[0]
        else:
            return result

    # }}}

    # {{{ add_constraints

    def obj_add_constraints(obj, constraints):
        """
        .. versionadded:: 2011.3
        """

        for cns in constraints:
            obj = obj.add_constraint(cns)

        return obj

    # }}}

    for c in [BasicSet, BasicMap, Set, Map]:
        c.project_out_except = obj_project_out_except
        c.remove_divs_of_dim_type = obj_remove_divs_of_dim_type
        c.add_constraints = obj_add_constraints





_add_functionality()

# vim: foldmethod=marker
