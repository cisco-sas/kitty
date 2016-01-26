# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Kitty.
#
# Kitty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Kitty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitty.  If not, see <http://www.gnu.org/licenses/>.

'''
Tests for low level fields
'''
from common import metaTest, BaseTestCase
from bitstring import Bits
from kitty.model.low_level.field import String, Static, Group
from kitty.model.low_level.container import Container, ForEach, If, IfNot, Repeat
from kitty.model.low_level.condition import Condition
from kitty.model.low_level.aliases import Equal, NotEqual


class ContainerTest(BaseTestCase):

    __meta__ = False

    def setUp(self, cls=Container):
        super(ContainerTest, self).setUp(cls)

    def get_default_container(self, fields=[], fuzzable=True):
        return self.cls(fields=fields, fuzzable=fuzzable)

    def _test_fields(self, init_fields=[], push_fields=[]):
        all_fields = init_fields + push_fields
        container = self.get_default_container(fields=init_fields, fuzzable=True)
        for f in push_fields:
            container.push(f)
            if isinstance(f, Container):
                # default is to pop the container immediatly in the tests...
                container.pop()
        fields_num_mutations = sum(f.num_mutations() for f in all_fields)
        container_num_mutations = container.num_mutations()
        self.assertEqual(fields_num_mutations, container_num_mutations)

        field_default_values = []
        for f in all_fields:
            field_default_values.append(f.render())
        fields_mutations = []
        for i, field in enumerate(all_fields):
            prefix = sum(field_default_values[:i])
            postfix = sum(field_default_values[i + 1:])
            if prefix == 0:
                prefix = Bits()
            if postfix == 0:
                postfix = Bits()
            while field.mutate():
                fields_mutations.append(prefix + field.render() + postfix)
            field.reset()
        container_mutations = self.get_all_mutations(container)
        self.assertListEqual(fields_mutations, container_mutations)

    @metaTest
    def test_primitives_init_1(self):
        fields = [String('test_%d' % d) for d in range(1)]
        self._test_fields(init_fields=fields)

    @metaTest
    def test_primitives_init_2(self):
        fields = [String('test_%d' % d) for d in range(2)]
        self._test_fields(init_fields=fields)

    @metaTest
    def test_primitives_init_5(self):
        fields = [String('test_%d' % d) for d in range(5)]
        self._test_fields(init_fields=fields)

    @metaTest
    def test_primitives_init_10(self):
        fields = [String('test_%d' % d) for d in range(10)]
        self._test_fields(init_fields=fields)

    @metaTest
    def test_primitives_push_1(self):
        fields = [String('test_%d' % d) for d in range(1)]
        self._test_fields(push_fields=fields)

    @metaTest
    def test_primitives_push_2(self):
        fields = [String('test_%d' % d) for d in range(2)]
        self._test_fields(push_fields=fields)

    @metaTest
    def test_primitives_push_5(self):
        fields = [String('test_%d' % d) for d in range(5)]
        self._test_fields(push_fields=fields)

    @metaTest
    def test_primitives_push_10(self):
        fields = [String('test_%d' % d) for d in range(10)]
        self._test_fields(push_fields=fields)

    @metaTest
    def test_primitives_init_1_push_1(self):
        init_fields = [
            String('test1'),
        ]
        push_fields = [
            String('test2'),
        ]
        self._test_fields(init_fields=init_fields, push_fields=push_fields)

    @metaTest
    def test_primitives_init_2_push_2(self):
        init_fields = [
            String('test11'),
            String('test12'),
        ]
        push_fields = [
            String('test21'),
            String('test22'),
        ]
        self._test_fields(init_fields=init_fields, push_fields=push_fields)

    @metaTest
    def test_containers_init_1(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(1)]
        self._test_fields(init_fields=containers)

    @metaTest
    def test_containers_init_2(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(2)]
        self._test_fields(init_fields=containers)

    @metaTest
    def test_containers_init_5(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(5)]
        self._test_fields(init_fields=containers)

    @metaTest
    def test_containers_init_10(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(10)]
        self._test_fields(init_fields=containers)

    @metaTest
    def test_containers_push_1(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(1)]
        self._test_fields(push_fields=containers)

    @metaTest
    def test_containers_push_2(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(2)]
        self._test_fields(push_fields=containers)

    @metaTest
    def test_containers_push_5(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(5)]
        self._test_fields(push_fields=containers)

    @metaTest
    def test_containers_push_10(self):
        containers = [Container(fields=[String('test_%d' % d)]) for d in range(10)]
        self._test_fields(push_fields=containers)

    @metaTest
    def test_containers_init_1_push_1(self):
        init_containers = [Container(fields=[String('test_init_%d' % d)]) for d in range(1)]
        push_containers = [Container(fields=[String('test_push_%d' % d)]) for d in range(1)]
        self._test_fields(init_fields=init_containers, push_fields=push_containers)

    @metaTest
    def test_containers_init_2_push_2(self):
        init_containers = [Container(fields=[String('test_init_%d' % d)]) for d in range(2)]
        push_containers = [Container(fields=[String('test_push_%d' % d)]) for d in range(2)]
        self._test_fields(init_fields=init_containers, push_fields=push_containers)

    def _test_not_fuzzable(self, fields):
        container = self.get_default_container(fields=fields, fuzzable=False)
        self.assertEqual(container.num_mutations(), 0)
        rendered = container.render()
        for i in range(10):
            self.assertFalse(container.mutate())
            self.assertEquals(container.render(), rendered)
        container.reset()
        for i in range(10):
            self.assertFalse(container.mutate())
            self.assertEquals(container.render(), rendered)

    @metaTest
    def test_not_fuzzable_1(self):
        fields = [String('test_%d' % d) for d in range(1)]
        self._test_not_fuzzable(fields)

    @metaTest
    def test_not_fuzzable_2(self):
        fields = [String('test_%d' % d) for d in range(2)]
        self._test_not_fuzzable(fields)

    @metaTest
    def test_not_fuzzable_5(self):
        fields = [String('test_%d' % d) for d in range(5)]
        self._test_not_fuzzable(fields)

    @metaTest
    def test_not_fuzzable_10(self):
        fields = [String('test_%d' % d) for d in range(10)]
        self._test_not_fuzzable(fields)

    @metaTest
    def test_hash_the_same_for_two_similar_objects(self):
        field1 = self.get_default_field()
        field2 = self.get_default_field()
        self.assertEqual(field1.hash(), field2.hash())

    @metaTest
    def test_hash_the_same_after_reset(self):
        field = self.get_default_field()
        hash_after_creation = field.hash()
        field.mutate()
        hash_after_mutate = field.hash()
        self.assertEqual(hash_after_creation, hash_after_mutate)
        field.reset()
        hash_after_reset = field.hash()
        self.assertEqual(hash_after_creation, hash_after_reset)
        while field.mutate():
            hash_after_mutate_all = field.hash()
            self.assertEqual(hash_after_creation, hash_after_mutate_all)
            field.render()
            hash_after_render_all = field.hash()
            self.assertEqual(hash_after_creation, hash_after_render_all)

    @metaTest
    def test_hash_the_same_for_two_similar_objects(self):
        container1 = self.get_default_container(fields=[String('test_string')])
        container2 = self.get_default_container(fields=[String('test_string')])
        self.assertEqual(container1.hash(), container2.hash())

    @metaTest
    def test_hash_the_same_after_reset(self):
        container = self.get_default_container(fields=[String('test_string')])
        hash_after_creation = container.hash()
        container.mutate()
        hash_after_mutate = container.hash()
        self.assertEqual(hash_after_creation, hash_after_mutate)
        container.reset()
        hash_after_reset = container.hash()
        self.assertEqual(hash_after_creation, hash_after_reset)
        while container.mutate():
            hash_after_mutate_all = container.hash()
            self.assertEqual(hash_after_creation, hash_after_mutate_all)
            container.render()
            hash_after_render_all = container.hash()
            self.assertEqual(hash_after_creation, hash_after_render_all)


class ConditionTest(ContainerTest):

    __meta__ = True
    condition_field_name = 'condition field'
    condition_field_value = 'condition value'
    inner_field_value = 'inner'

    def setUp(self, cls=None):
        super(ConditionTest, self).setUp(cls)

    class AlwaysTrue(Condition):
        def applies(self, container):
            return True

    class AlwaysFalse(Condition):
        def applies(self, container):
            return False

    def get_default_container(self, fields=[], fuzzable=True):
        return self.cls(condition=self.get_applies_always_condition(), fields=fields, fuzzable=fuzzable)

    def get_applies_first_condition(self):
        return None

    def get_not_applies_first_condition(self):
        return None

    def get_applies_always_condition(self):
        return None

    def get_not_applies_always_condition(self):
        return None

    def get_condition_field(self):
        return String(name=ConditionTest.condition_field_name, value=ConditionTest.condition_field_value)

    @metaTest
    def test_condition_not_applies_always(self):
        field = self.get_condition_field()
        condition = self.get_not_applies_always_condition()
        condition_container = self.cls(condition=condition, fields=[String(ConditionTest.inner_field_value)], fuzzable=True)
        # This is done to allow field name resolution
        enclosing = Container(fields=[field, condition_container])
        rendered = condition_container.render()
        self.assertEqual(rendered, Bits())
        while condition_container.mutate():
            rendered = condition_container.render()
            self.assertEqual(rendered, Bits())

    @metaTest
    def test_condition_applies_first(self):
        field = self.get_condition_field()
        condition = self.get_applies_first_condition()
        inner_field = String(ConditionTest.inner_field_value)
        condition_container = self.cls(condition=condition, fields=[inner_field], fuzzable=True)
        # This is done to allow field name resolution
        enclosing = Container(fields=[field, condition_container])
        self.assertEqual(condition_container.render(), inner_field.render())
        while condition_container.mutate():
            self.assertEqual(condition_container.render(), inner_field.render())

        condition_container.reset()
        field.mutate()
        self.assertEqual(condition_container.render(), Bits())
        while condition_container.mutate():
            self.assertEqual(condition_container.render(), Bits())

    @metaTest
    def test_condition_not_applies_first(self):
        field = self.get_condition_field()
        condition = self.get_not_applies_first_condition()
        inner_field = String(ConditionTest.inner_field_value)
        condition_container = self.cls(condition=condition, fields=[inner_field], fuzzable=True)
        # This is done to allow field name resolution
        enclosing = Container(fields=[field, condition_container])
        self.assertEqual(condition_container.render(), Bits())
        while condition_container.mutate():
            self.assertEqual(condition_container.render(), Bits())

        condition_container.reset()
        field.mutate()
        self.assertEqual(condition_container.render(), inner_field.render())
        while condition_container.mutate():
            self.assertEqual(condition_container.render(), inner_field.render())


class IfTest(ConditionTest):

    __meta__ = False

    def setUp(self, cls=If):
        super(IfTest, self).setUp(cls)

    def get_applies_first_condition(self):
        return Equal(ConditionTest.condition_field_name, ConditionTest.condition_field_value)

    def get_not_applies_first_condition(self):
        return NotEqual(ConditionTest.condition_field_name, ConditionTest.condition_field_value)

    def get_applies_always_condition(self):
        return ConditionTest.AlwaysTrue()

    def get_not_applies_always_condition(self):
        return ConditionTest.AlwaysFalse()


class IfNotTest(ConditionTest):

    __meta__ = False

    def setUp(self, cls=IfNot):
        super(IfNotTest, self).setUp(cls)

    def get_applies_first_condition(self):
        return NotEqual(ConditionTest.condition_field_name, ConditionTest.condition_field_value)

    def get_not_applies_first_condition(self):
        return Equal(ConditionTest.condition_field_name, ConditionTest.condition_field_value)

    def get_applies_always_condition(self):
        return ConditionTest.AlwaysFalse()

    def get_not_applies_always_condition(self):
        return ConditionTest.AlwaysTrue()


class ForEachTests(ContainerTest):

    __meta__ = False

    def setUp(self, cls=ForEach):
        super(ForEachTests, self).setUp(cls)

    def get_default_container(self, fields=[], fuzzable=True, mutated_field=None):
        if mutated_field is None:
            mutated_field = Static('static field')
        return ForEach(mutated_field=mutated_field, fields=fields, fuzzable=fuzzable)

    def _test_basic(self, mutated, field):
        container = ForEach(mutated_field=mutated, fields=[field])
        expected_num_mutations = mutated.num_mutations() * field.num_mutations()
        container_num_mutations = container.num_mutations()
        self.assertEqual(container_num_mutations, expected_num_mutations)
        fields_mutations = self.get_all_mutations(field)
        container_mutations = self.get_all_mutations(container)
        self.assertListEqual(container_mutations, fields_mutations * mutated.num_mutations())

    def _test_mutating_mutated(self, mutated, field):
        foreach = ForEach(mutated_field=mutated, fields=[field])
        container = Container(fields=[mutated, foreach])
        expected_num_mutations = mutated.num_mutations() * field.num_mutations() + mutated.num_mutations()
        container_num_mutations = container.num_mutations()
        self.assertEqual(container_num_mutations, expected_num_mutations)
        mutated_mutations = self.get_all_mutations(mutated)
        fields_mutations = self.get_all_mutations(field)
        expected_mutations = []
        for mutation in mutated_mutations:
            expected_mutations.append(mutation + field.render())
        for gmutation in mutated_mutations:
            for fmutation in fields_mutations:
                expected_mutations.append(gmutation + fmutation)
        container_mutations = self.get_all_mutations(container)
        self.assertListEqual(container_mutations, expected_mutations)

    def test_group_group(self):
        mutated = Group(values=['1', '2', '3'])
        field = Group(values=['a', 'b', 'c'])
        self._test_basic(mutated, field)

    def test_group_group_mutating_mutated_field(self):
        mutated = Group(values=['1', '2', '3'])
        field = Group(values=['a', 'b', 'c'])
        self._test_mutating_mutated(mutated, field)

    def test_group_string(self):
        mutated = Group(values=['1', '2', '3'])
        field = String('best')
        self._test_basic(mutated, field)

    def test_group_string_mutating_mutated_field(self):
        mutated = Group(values=['1', '2', '3'])
        field = String('best')
        self._test_mutating_mutated(mutated, field)

    def test_string_string(self):
        mutated = String('test')
        field = String('best')
        self._test_basic(mutated, field)

    def test_string_string_mutating_mutated_field(self):
        mutated = String('test')
        field = String('best')
        self._test_mutating_mutated(mutated, field)

    def test_string_group(self):
        mutated = String('test')
        field = Group(values=['a', 'b', 'c'])
        self._test_basic(mutated, field)

    def test_string_group_mutating_mutated_field(self):
        mutated = String('test')
        field = Group(values=['a', 'b', 'c'])
        self._test_mutating_mutated(mutated, field)


class RepeatTest(ContainerTest):

    __meta__ = False

    def setUp(self, cls=Repeat):
        super(RepeatTest, self).setUp(cls)

    def get_default_container(self, fields=[], fuzzable=True):
        return Repeat(fields=fields, fuzzable=fuzzable)

    def _test_mutations(self, repeater, fields, min_times=1, max_times=1, step=1):
        repeats = max_times - min_times / step
        expected_num_mutations = sum(f.num_mutations() for f in fields) + repeats
        repeater_num_mutations = repeater.num_mutations()
        self.assertEqual(repeater_num_mutations, expected_num_mutations)

        field_default_values = [field.render() for field in fields]
        fields_mutations = []
        for i in range(min_times, max_times, step):
            fields_mutations.append(sum(field_default_values) * i)
        for j, field in enumerate(fields):
            prefix = sum(field_default_values[:j])
            postfix = sum(field_default_values[j + 1:])
            if prefix == 0:
                prefix = Bits()
            if postfix == 0:
                postfix = Bits()
            while field.mutate():
                fields_mutations.append((prefix + field.render() + postfix) * min_times)
            field.reset()
        repeater.reset()
        repeater_mutations = self.get_all_mutations(repeater)
        self.assertListEqual(fields_mutations, repeater_mutations)

    def test_repeat_single_max_times_1(self):
        max_times = 1
        fields = [
            String('field1')
        ]
        repeater = Repeat(fields=fields, max_times=max_times)
        self._test_mutations(repeater, fields, max_times=max_times)

    def test_repeat_single_max_times_5(self):
        max_times = 5
        fields = [
            String('field1')
        ]
        repeater = Repeat(fields=fields, max_times=max_times)
        self._test_mutations(repeater, fields, max_times=max_times)
