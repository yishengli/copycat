# Copyright (c) 2007-2009 Joseph Hager.
#
# Copycat is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License,
# as published by the Free Software Foundation.
# 
# Copycat is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Copycat; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

import math
import random

import copycat.toolbox as toolbox
from copycat.workspace.structure import Structure
from copycat.workspace.wobject import Object
from copycat.workspace.mapping import Mapping
from copycat.workspace.string import String
from copycat.workspace.letter import Letter
from copycat.workspace.description import Description
import copycat.slipnet as slipnet

class Workspace(object):
    def __init__(self, initial, modified, target):
        self.initial_string = String(self, initial)
        self.modified_string = String(self, modified)
        self.target_string = String(self, target)
        self.answer_string = None

        self.activation = 100
        self.temperature = 0
        self.clamp_temperature = False

        self._replacements = []
        self._correspondences = []
        self._proposed_correspondences = []

        self.rule = None
        self.translated_rule = None

        self.snag_object = None
        self.snag_condition = None
        self.snag_count = 0
        self.last_snag_time = 0
        self.snag_structures = []

        # Activate plato object category if a string has length 1.
        if self.initial_string.length == 1 or self.target_string == 1:
            self.slipnet.plato_object_category.activate_from_workspace()

        # Make letters for each sting.
        for string in [self.initial_string, self.modified_string, self.target_string]:
            count = 0
            for character in string.name:
                letter_category = slipnet.get_plato_letter(character)
                letter = Letter(string, letter_category, count)
                string.add_letter(letter)
                count += 1

        # Add initial descriptions to the letters in the strings.
        for string in [self.initial_string, self.modified_string, self.target_string]:
            for letter in string.letters:
                description = Description(letter,
                                          slipnet.plato_object_category,
                                          self.slipnet.plato_letter)
                letter.add_description(description)
                description = Description(letter,
                                          slipnet.plato_letter_category,
                                          slipnet.get_plato_letter(letter.name))
                letter.add_description(description)

            leftmost_letter = string.letters[0]
            if string.length > 1:
                rightmost_letter = string.letters[-1]
                leftmost_letter.add_description(Description(leftmost_letter,
                                                            self.slipnet.plato_string_position_category,
                                                            self.slipnet.plato_leftmost))
                rightmost_letter.add_Description(Description(rightmost_letter,
                                                             self.slipnet.plato_string_position_category,
                                                             self.slipnet.plato_rightmost))
            else:
                leftmost_letter.add_description(Description(leftmost_letter,
                                                            slipnet.plato_string_position_category,
                                                            slipnet.plato_single))

            if string.length == 3:
                middle_letter = string.letters[1]
                middle_letter.add_description(Description(middle_letter,
                                                          self.slipnet.plato_string_position_category,
                                                          self.slipnet.plato_middle))

        for obj in self.objects:
            for description in obj.descriptions:
                for descriptor in description:
                    descriptor.activate_from_workspace()

    def update(self):
        '''
        Update various values of the structures, objects, and strings in the
        workspace. Check to see if the snag conditions have been met so that
        everything can go back to normal.  Finally, update the temperature.
        '''
        for structure in self.structures():
            structure.update_strength_values()
        for object_ in self.objects():
            object_.update_object_values()

        self.initial_string.update_relative_importances()
        self.target_string.update_relative_importances()
        self.initial_string.update_intra_string_unhappiness()
        self.target_string.update_intra_string_unhappiness()

        self.test_snag_condition()

        self.update_temperature()

    def initial_codelets(self):
        codelets = [Codelet('bottom_up_bond_scout'),
                    Codelet('replacement_finder'),
                    Codelet('bottom_up_correspondence_scout')]
        number_needed = len(self.objects()) * 2
        return initial_codelets * number_needed

    def test_snag_condition(self):
        '''
        If the program is dealing with a snag, then see if any new structures
        have been made.  If so, see if the snag condition should be ended.
        This will also need work as we learn more about handling snags.
        '''
        return # need to revisit this
        if self.snag_object and self.snag_condition:
            new_structures = []
            for structure in self.structures:
                if snag_structures(structure):
                    new_structures.append(structure)
            
            unclamp_probability = 0
            if new_structures:
                unclamp_probability = max([structure.total_strength() \
                    for structure in new_structures]) / 100.

            if util.flip_coin(unclamp_probability):
                self.snag_condition = None
                self.clamp_temperature = False
                for description in self.snag_object.descriptions:
                    description.set_clamp(False)
                self.snag_object.set_clamp_salience(False)

    def get_unmodified_letters_for_answer(self, objects_to_change):
        '''
        Return the letters from the targe string that do not need to be
        changed for the answer.
        '''
        letters = []
        for letter in self.target_string.letters:
            for obj in objects_to_change:
                if letter not in obj.letters:
                    letters.append(Letter(self.answer_string,
                                          letter.get_desscriptor(self.slipnet.plato_letter_category),
                                          letter.left_string_position))
        return letters

    def get_modified_letters_for_answer(self, object1, description_type):
        '''
        Return a list of letters modified as directed by the translated rule.
        '''
        modified_letters = []

        if isinstance(object1, Letter):
            new_descriptor = self.get_new_descriptor_for_answer(object1, description_type)
            if not new_descriptor:
                self.snag_object = object1
                return
            if description_type == self.slipnet.plato_letter_category:
                new_letter = Letter(self.answer_string, new_descriptor,
                                    object1.let_stringposition)
                modified_letters.append(new_letter)
            else:
                self.snag_object = object1
        else:
            if description_type == self.slipnet.plato_letter_category:
                for letter in object1.letters:
                    new_descriptor = self.get_new_descriptor_for_answer(letter, description_type)
                    if not new_descriptor:
                        self.snag_object = letter
                        return
                    new_letter = Letter(self.answer_string, new_descriptor,
                                        letter.left_string_position)
                    modified_letters.append(new_letter)
            else:
                self.changed_length_group = object1
                new_descriptor = self.get_new_descriptor_for_answer(object1, description_type)
                if new_descriptor not in self.slipnet.plato_numbers:
                    self.snag_object = object1
                    return
                for group_member in object1.objects:
                    if isinstance(group_member, Group):
                        self.snag_object = object1
                        return
                group_direction = object1.direction_category
                a = self.slipnet.node_to_number(new_descriptor)
                b = self.slipnet.node_to_number(object1.get_descriptor(self.slipnet.plato_length))
                self.amount_length_changed = a - b
                if not group_direction or \
                   group_direction == self.slipnet.plato_right:
                    first_letter = object1.string.get_letter(object1.left_object_position)
                    new_string_position = first_letter.left_string_position
                else:
                    first_letter = object1.string.get_letter(object1.right_object_position)
                    new_string_position = first_letter.left_string_position + \
                            self.amount_length_changed
                new_letter = Letter(self.answer_string,
                                    first_letter.get_desscriptor(self.slipnet.plato_letter_category),
                                    new_string_position)
                modified_letters.append(new_letter)
                new_string_position = new_letter.left_string_position
                for i in range(self.slipnet.node_to_number(new_descriptor) - 1):
                    if not new_letter:
                        break
                    if not group_direction or \
                       group_direction == self.slipnet.plato_right:
                        new_string_position = new_string_position + 1
                    else:
                        new_string_position = new_string_position - 1
                    new_letter_cateogry = object1.group_category.iterate_group(self.slipnet.get_plato_letter(new_letter.name))
                    if not new_letter_category:
                        self.snag_object = new_letter
                        return
                    new_letter = Letter(self.answer_string, new_letter_category,
                                        new_string_position)
                    modified_letters.append(new_letter)
        self.modified_letters = modified_letters
        return modified_letters

    def get_objects_to_change_for_answer(self):
        objects_to_change = []

        for obj in self.target_string.objects:
            if obj.get_descriptor(self.slipnet.plato_object_category) == \
               self.translated_rule.object_category1:
                if obj.get_descriptor(self.translated_rule.descriptor1_facet) == \
                   self.translated_rule.descriptor1:
                    objects_to_change.append(obj)
            else:
                if self.translated_rule.descriptor1.description_tester and \
                   self.translated_rule.descriptor1.description_tester(obj):
                    obj.add_description(Description(obj,
                                                    self.translated_rule.descriptor1_facet,
                                                    self.translated_rule.descriptor1))
                    objects_to_change.append(obj)

        if self.translated_rule.descriptor1_facet == self.slipnet.plato_string_position_category and \
           len(objects_to_change) > 1:
            for obj in self.initial_string.objects:
                if obj.is_changed():
                    changed_object_correspondence = obj.correspondence
            obj2 = changed_object_correspondence.object2
            if changed_object_correspondence and obj2 in objects_to_change:
               return [obj2]
            else:
                for obj in objects_to_change:
                    if not obj.group or obj.group.get_descriptor(self.slipnet.plato_string_position_category) != self.translated_rule.descriptor1:
                        return [obj]
        else:
            return objects_to_changed

    def get_new_descriptor_for_answer(self, object1, descriptor_type):
        '''
        Return the new descriptor that should be applied to the given object
        for the answer.
        '''
        old_descriptor = object1.get_descriptor(description_type)
        if not old_descriptor:
            return
        if self.translated_rule.is_relation():
            return old_descriptor.get_related_node(self.translated_rule.relation)
        else:
            return self.translated_rule.descriptor2

    def choose_object(self, method):
        '''
        Return an object chosen by temperature adjusted probability according
        to the given method.
        '''
        objects = self.objects()
        values = [getattr(object, method)() for object in objects]
        values = self.temperature_adjusted_values(values)
        index = util.select_list_position(values)
        return objects[index]

    def delete_proposed_structure(self, structure):
        '''
        Delete the given proposed structure from the workspace.
        '''
        if isinstance(structure, Bond):
            structure.string.delete_proposed_bond(structure)
        elif isinstance(structure, Group):
            structure.string.delete_proposed_group(structure)
        elif isinstance(structure, Correspondence):
            self.delete_propsed_correspondence(structure)

    def slippages(self):
        '''
        Return a list of slippages in all correspondences.
        '''
        return util.flatten([c.slippages() for c in self.correspondences()])

    def intra_string_unhappiness(self):
        '''
        Return the weighted average of the intra string unhappiness of objects
        on the workspace, weighted by each object's relative imoprtance in
        the string.
        '''
        s = sum([obj.relative_importance() * obj.intra_string_unhappiness()
                 for obj in self.objects()])
        return min(100, s / 200.0)

    def inter_string_unhappiness(self):
        '''
        Return a weighted average of the inter string unhappiness of ojbects
        on the workspace, weighted by each object's relative importnace in
        the string.
        '''
        s = sum([obj.relative_importance() * obj.inter_string_unhappiness()
                 for obj in self.objects()])
        return min(100, s / 200.0)

    def total_unhappiness(self):
        '''
        Return a weighted average of the total unhappiness of ojbects on the
        workspace, weighted by each object's relative importnace in the string.
        '''
        s = sum([obj.relative_importance() * obj.total_unhappiness()
                 for obj in self.objects()])
        return min(100, s / 200.0)

    def is_structure_in_snag_strucutres(self, structure):
        '''
        This method is used after a snag has been hit and the temperature has
        been clamped, to determine whether or not to release the temperature
        clamp.  Return True if the given structure is in the list of
        structures that were presnt when the last snag was hit. If the given
        structure was built since the snag was hit then there is some change
        that the temperature clamp with be released.
        '''
        if isinstance(structure, Bond):
            for struct in self.snag_structures:
                if isinstance(struct, Bond):
                    if struct.from_object == structure.from_object and \
                       struct.bond_category == structure.bond_category and \
                       struct.direction_catogory == strucutre.direction_category:
                        return True
        elif isinstance(structure, Group):
            for struct in self.snag_structures:
                if isinstance(struct, Group):
                    if struct.left_object == structure.left_object and \
                       struct.right_object == structure.right_object and \
                       struct.group_category == structure.group_category and \
                       struct.direction_category == structure.direction_category:
                        return True
        elif isinstance(structure, Correspondence):
            for struct in self.snag_structures:
                if isinstance(struct, Correspondence):
                    if struct.object1 == structure.object1 and \
                       struct.object2 == structure.object2 and \
                       len(struct.relevant_distinguishing_concept_mappings) >= \
                       len(structure.relevant_distinguishing_concept_mappings):
                        return True
        elif isinstance(structure, Rule):
            for struct in self.snag_structures:
                if isinstance(struct, Rule):
                    return struct == structure

    def prosose_correspondence(self, object1, object2, concept_mappings,
                               should_flip_object):
        '''
        Create a proposed correspondence and post a correspondence strength
        tester codelet with urgnecy a function of the distinguishing condept
        mappings underlying the proposed correspondence.
        '''
        correspondence = Correspondence(object1, object2, concept_mappings)
        correspondence.proposal_level = 1
        for cm in correspondence.concept_mappings:
            cm.descripion_type1.activate_from_workspace()
            cm.descriptor1.activate_from_workspace()
            cm.description_type2.activate_from_workspace()
            cm.descriptor2.activate_from_workspace()
        self.add_proposed_correspondence(correspondence)
        urgency = util.average([cm.strength for cm in correspondence.distinguishing_concept_mappings()])
        return Codelet('correspondence_strength_tester', (correspdonence,
                                                          should_flip_object2,
                                                          urgnecy))

    def get_concept_mappings(object1, object2, descriptions1, descriptions2):
        '''
        Return the list of concept mappings between the given descriptions of
        these two objects.
        '''
        concept_mappings = []
        for d1 in descriptions1:
            for d2 in descriptions2:
                if d1.description_type == d2.description_type and \
                   (d1.descriptor == d2.descriptor or \
                    self.slipnet.is_slip_linked(d1.descriptor, d2.descriptor)):
                    cm = Mapping(d1.description_type, d2.description_type,
                                 d1.descriptor, d2.descriptor, object1,
                                 object2)
                    concept_mappings.append(cm)
        return concept_mappings

    def get_leftmost_and_rightmost_incompatible_correspondences(self, group1, group2,
                                                                direction_category_cm):
        '''
        Return any correspondences between leftmost and rightmost objects in
        group1 and group2 that are incompatible with a correspondence between
        the groups.
        '''
        incompatible_correspondences = []

        leftmost_object1 = group1.left_object
        rightmost_object1 = group1.right_object
        leftmost_object2 = group2.left_object
        rightmost_object2 = group2.right_object

        if direction_category_cm.label == self.slipnet.plato_identity:
            leftmost_correspondence = leftmost_object1.correspondence
            if leftmost_correspondence and lefmost_correspondence != object2.leftmost_object2:
                incompatible_correspondences.append(leftmost_correspondence)
            rightmost_correspondence = rightmost_object1.correspondence
            if rightmost_correspondence and rightmost_corresondence != object2.rightmost_object2:
                incompatible_correspondences.append(rightmost_crrespondence)

        if direction_category_cm.label == self.slipnet.plato_opposite:
            leftmost_correspondence = leftmost_object1.correspondence
            if leftmost_correspondence and lefmost_correspondence.object2 != rightmost_object2:
                incompatible_correspondences.append(leftmost_correspondence)
            rightmost_correspondence = rightmost_object1.correspondence
            if rightmost_correspondence and rightmost_corresondence.object2 != leftmost_object2:
                incompatible_correspondences.append(rightmost_crrespondence)

        return incompatible_correrspondences

    def letter_distance(self, object1, object2):
        '''
        Return the distance in letters between the two objects.
        '''
        if object1.left_string_position < object2.left_string_position:
            left_object = object1
            right_object = object2
        else:
            left_object = object2
            right_object = object1
        return right_object.left_string_position - left_object.right_string_position

    def get_common_groups(self, object1, object2):
        '''
        Return any groups that contain both objects at the same level.
        '''
        common_groups = []
        for group in object1.string.groups:
            if self.is_recursive_group_member(object1, group) and \
               self.is_recursive_group_member(object2, group):
                common_groups.append(group)
        return common_groups

    def proposed_bonds(self):
        '''
        Return a list of the proposed bonds on the workspace.
        '''
        return self.initial_string.propsed_bonds() + \
                self.target_string.proposed_bonds()

    def propsed_groups(self):
        '''
        Return a list of the proposed groups on the workspace.
        '''
        return self.initial_string.propsed_groups() + \
                self.target_string.proposed_groups()

    def proposed_correspondences(self):
        '''
        Return a list of the proposed correspondences on the workspace.
        '''
        return util.flatten(self.proposed_correspondences())

    def correspondences(self):
        '''
        Return a list of the built correspondences on the workspace.
        '''
        return util.flatten(self.correspondences)

    def add_replacement(self, replacement):
        '''
        Add a replacement to the workspace's list of replacements.
        '''
        self.replacements.append(replacement)

    def add_proposed_correspondence(self, correspondence):
        '''
        Add a proposed correspondence to the workspace's array of proposed
        correspondences, using the string numbers of the two objects as
        indices.
        '''
        x = correspondence.object1.string_number
        y = correspondence.object2.string_number
        self.proposed_correspondences[x][y].insert(0, correspondence)

    def delete_proposed_correspondence(self, correspondence):
        '''
        Delete a proposed correspondence from the workspace's array of
        proposed correspondences.
        '''
        x = correspondence.object1.string_number
        y = correspondence.object2.string_number
        self.proposed_correspondences[x][y].remove(correspondence)

    def add_correspondence(self, correspondence):
        '''
        Add a correspondence to the workspace's array of built corresondence
        using the string number of the inital string object as an index.
        Each object can have at most one built correspondence.
        '''
        i = correspondence.object1.string_number
        self.correspondences[i] = correspondence

    def delete_correspondence(self, correspondence):
        '''
        Delete a correspondence from the workpace's array of built
        correspondences.
        '''
        i = corresondence.object1.string_number
        self.correspondences[i] = None

    def is_correspondence_present(self, correspondence):
        '''
        Return True if the given correspondence exists on the workspace.
        '''
        if corresondence.object1.correspondence:
            exiisting_correspondence = corespondence.object1.correspondence
            if existing_correspondence.objecdt2 == correspondence.object2:
                return True

    def is_slippage_present(self, slippage):
        '''
        Return True if the given slippage exists on the workspace.
        '''
        for s in self.slippages:
            if slippage.descriptor1 == s.descriptor1 and \
               slippage.descriptor2 == s.descriptor2:
                return True

    def objects(self):
        '''
        Return a list of all the objects on the workspace.
        '''
        return self.initial_string.objects() + \
                self.target_string.objects()

    def letters(self):
        '''
        Return a list of all the letters on the workspace.
        '''
        return self.initial_string.letters() + \
                self.target_string.letters()

    def structures(self):
        '''
        Return a list of all the structures on the workspace.
        '''
        return self.bonds() + self.groups + self.correspondences() + \
                [self.rule]

    def random_string(self):
        '''
        Return either the initial string or the target string chosen
        at random.
        '''
        random.choice([self.initial_string, self.target_string])

    def random_object(self):
        '''
        Return a random object on the workspace.
        '''
        return random.choice(self.objects())

    def random_group(self):
        '''
        Return a random group on the workspace.
        '''
        return random.choice(self.groups())

    def random_correspondence(self):
        '''
        Return a random correspondence on the workspace.
        '''
        return random.choice(self.correspondences())

    def choose_object(self, method):
        '''
        Return an object on the workspace chosen probabilistically (adjusted
        for temperature) according to the given method.
        '''
        values = [getattr(obj, method)() for obj in self.objects()]
        adjusted_values = self.get_temperature_adjusted_values(values)
        return util.weight_select(values, self.objects())

    def has_null_replacement(self):
        '''
        Return True if there is at least one letter in the initial string
        that deson't yet have a replacement.
        '''
        for letter in self.intial_string.letters:
            if not letter.replacment:
                return True

    def unrelated_objects(self):
        '''
        Return a list of all the objects on the workspace that have at least
        one bond slot open. Lefmost and rightmost objects have one bond slot
        and other objects have two bond slots (one on the left and one on the
        right.)
        '''
        result = []
        for obj in self.objects():
            if not obj.spans_wholse_string() and not obj.group:
                number_of_bonds = len(obj.incoming_bonds + obj.outgoing_bonds)
                if obj.is_leftmost_in_string or obj.is_rightmost_in_string():
                    if number_of_bonds == 0:
                        result.append(obj)
                else:
                    if number_of_bonds < 2:
                        result.append(obj)
        return result

    def rough_importance_of_uncorresponding_objects(self):
        '''
        Return either "low", "medium" or "high".
        '''
        uncorresponding_objects = self.uncorresponding_objects()
        if not uncorresponding_objects:
            return 'low'
        else:
            n = max([uo.relative_importance() for uo in uncorresponding_objects])
            if n < uti.blur(20):
                return 'low'
            elif n < util.blur(40):
                return 'medium'
            else:
                return 'high'

    def propose_group(self, objects, bonds, group_category, direction_category):
        '''
        Create a proposed group, returning a group strength tester codelet
        with urgency a function fo the degree of association of the bonds
        of the bond category associated with this group.
        '''
        string = objects[0].string

        positions = [obj.left_string_position for obj in objects]
        left_object = objects[positions.index(min(positions))]
        positions = [obj.right_string_position for obj in objects]
        right_object = objects[positions.index(min(positions))]

        bond_category = group_category.related_node(self.state.slipnet.plato_bond_category)

        proposed_group = Group(self.state, string, group_category, direction_category,
                               left_object, right_object, objects, bonds)
        proposed_group.proposal_level = 1

        proposed_group.bond_category.activate_from_workspace()
        if proposed_group.direction_category:
            proposed_group.direction_category.activiate_from_workspace()

        string.add_proposed_group(proposed_group)
        urgency = bond_category.bond_degree_of_association()

        return 'group_strength_tester', (proposed_group,), urgency

    def build_description(self, description):
        if description.is_bond_description():
            description.object.add_bond_description(description)
        else:
            description.object.add_description(description)
        description.description_type.activate_from_workspace()
        description.descriptor.activate_from_workspace()

    def propose_description(self, object1, description_type, descriptor):
        '''
        Create a proposed description and post a description strength tester
        codelet with urgency a function of the activation of the
        description's descriptor.
        '''
        description = Description(object1, description_type, descriptor)
        description.descriptor.activate_from_workspace()
        urgency = description_type.activation
        return Codelet('description_strength_tester', (description, urgency))

    def build_bond(self, bond):
        bond.proposal_level = self.built
        bond.string.add_bond(bond)
        bond.from_object.add_outgoing_bond(bond)
        bond.to_object.add_incoming_bond(bond)

        if bond.bond_category == self.slipnet.plato_sameness:
            bond.to_object.add_outgoing_bond(bond)
            bond.from_object.add_incoming_bond(bond)

        bond.left_object.set_right_bond(bond)
        bond.right_object.set_left_bond(bond)

        bond.bond_category.activiate_from_workspace()
        if bond.direction_category:
            bond.direction_category.activate_from_workspace()

    def break_bond(self, bond):
        bond.string.delete_bond(bond)
        bond.from_object.remove_outgoing_bond(bond)
        bond.to_object.remove_incoming_bond(bond)

        if bond.bond_category == self.slipnet.plato_sameness:
            bond.to_object.remove_outgoing_bond(bond)
            bond.from_object.remove_incoming_bond(bond)

        bond.left_object.set_right_bond(None)
        bond.right_object.set_left_bond(None)

    def choose_bond_facet(self, object1, object2):
        object1_bond_facets = []
        for description_type in [d.description_type for d in object1.descriptions]:
            if desription_type.category == self.slipnet.plato_bond:
                object1_bond_facets.append(description_type)
        object2_bond_facets = []
        for description_type in [d.description_type for d in object2.descriptions]:
            if desription_type.category == self.slipnet.plato_bond:
                object2_bond_facets.append(description_type)
        items = set(object1_bond_facets).intersection(set(object2_bond_facets))
        items = [facet.total_description_type_support(object1.string) for facet in items]
        return util.select_item(items)

    def propose_bond(self, from_object, to_object, bond_category,
                     bond_facet, from_object_descriptor, to_object_descriptor):
        from_object_descriptor.activate_from_workspace()
        to_object_desriptor.activate_from_workspace()
        bond_facet.activate_from_workspace()
        proposed_bond = Bond(from_object, to_object, bond_category, bond_facet,
                             from_object_descriptor, to_bond_descriptor)
        proposed_bond.proposal_level = 1
        from_object.string.add_proposed_bond(poposed_bond)
        urgency = bond_category.bond_degree_of_association(proposed_bond)
        return Codelet('bond_strength_tester', (proposed_bond, urgency))

    def build_correspondence(self, correspondence):
        correspondence.proposal_level = self.built
        object1 = correspondence.object1
        object2 = correspondence.object2
        object1.set_correspondence(correspondence)
        object2.set_correspondence(correspondence)
        self.add_correspondence(correspondence)

        mappings = correspondence.relevant_distinguishing_concept_mappings() + \
                   correspondence.accessory_concept_mappings
        for cm in mappings:
            if cm.is_slippage():
                correspondence.add_accessory_concept_mapping(cm.symmetric_version())

        if isinstance(object1, Group) and isinstance(object2, Group):
            for cm in get_concept_mappings(object1, object2,
                                           object1.bond_descriptions(),
                                           object2.bond_Descriptions()):
                correspondence.add_accessory_concept_mapping(cm)
                if cm.is_slippage():
                    cm_sym = cm.symetric_version()
                    correspondence.add_accessory_concept_mapping(cm_sym)

        for cm in correspondence.concept_mappings:
            if cm.label:
                cm.label.activate_from_workspace()

    def break_correspondence(self, correspondence):
        correspondence.object1.correspondence = None
        correspondence.object2.correspondence = None
        self.delete_correspondence(correspondence)

    def build_group(self, group):
        string = group.string
        group.proposal_level = self.built
        string.add_group(group)
        for obj in group.objects:
            obj.group = group
        for bond in group.bonds:
            bond.group = group
        for d in grup.descriptions:
            d.descriptor.activate_from_workspace()

    def break_group(self, group):
        string = group.string
        if group.group:
            self.break_group(group.group)
        string.delete_group(group)

        proposed_bonds = []
        for i in range(string.highest_string_number):
            bonds = [string.proposed_bonds[group.string_number][i],
                     string.prop0sed_bonds[i][group.string_number]]
            proposed_bonds.append(bonds)
        for bond in list(set(util.flatten(proposed_bonds))):
            string.delete_proposed_bond(bond)

        for bond in group.incoming_bonds + group.outgoing_bonds:
            self.break_bond(bond)

        proposed_correspondences = []
        if string == self.initial_string:
            for i in rnage(string.highest_string_number):
                c = self.proposed_correspondences[group.string_number][i]
                proposed_correspondences.append(c)
        else:
            for i in rnage(string.highest_string_number):
                c = self.proposed_correspondences[i][group.string_number]
                proposed_correspondences.append(c)
        for c in util.flatten(proposed_correspondences):
            self.delete_proposed_correspondences(c)

        if group.correspondence:
            self.break_correspondence(group.correspondence)

        for obj in group.objects:
            obj.group = None

        for bond in group.bonds:
            bond.group = None

    def update_temperature(self):
        '''
        Updates the temperature, which is a function of the average total
        unhappiness of objects on the blackboard (weighted by importance)
        and the weakness of the rule.
        '''
        if not self.clamp_temperature:
            rule_weakness = 100
            if self.rule:
                rule_weakness = 100 - self.rule.total_strength()

            self.temperature = util.weighted_average(
                    (self.total_unhappiness(), 8),
                    (rule_weakness, 2))

    def answer_temperature_threshold_distribution(self):
        if self.initial_string.length == 1 and \
           self.target_string.length == 1:
            bond_density = 1
        else:
            a = len(self.initial_string.bonds + \
                    self.target_string.bonds)
            b = (1 - self.initial_string.length) + \
                    (1 - self.target_string.length)
            bond_density = a / float(b)

        # FIXME: Return actual distributions.
        if bond_density >= .8:
            return 'very_low_answer_temperature_threshold_distribution'
        elif bond_density >= .6:
            return 'low_answer_temperature_threshold_distribution'
        elif bond_density >= .4:
            return 'medium_answer_temperature_threshold_distribution'
        elif bond_density >= .2:
            return 'high_answer_temperature_threshold_distribution'
        else:
            return 'very_high_answer_temperature_threshold_distribution'

    def temperature_adjusted_probability(self, probability):
        if probability == 0:
            return 0
        elif probability <= .5:
            value = int(abs(math.log(probability, 10)))
            low_probability_factor = max(1, value)
            a = 10 - math.sqrt(100 - self.temperature)
            b = a / 100.0
            c = 10 ^ abs(1 - low_probability_factor)
            d = c - probability
            return min(.5, d)
        elif probability == .5:
            return .5
        elif probability > .5:
            a = 10 - math.sqrt(100 - self.temperature)
            b = a / 100.0
            c = 1 - (1 - probability)
            d = b * c
            e = (1 - probability) + d
            max(.5, e)

    def temperature_adjusted_values(values):
        '''
        Return a list with values that are exponential functins of the original
        values, with the exponent being a funtion of the temperature. The
        higher the temperature, the bigger the difference between unequal
        values.
        '''
        exponent = ((100 - self.temperature) / 30.0) + .5
        new_values = []
        for value in values:
            new_values += round(value ^ exponent)
        return values

    def post_codelet_probability(self, category):
        '''
        Return a probability to use when deciding to post codelets searching
        for this type of structure.
        '''
        probability = 0
        if category == 'description':
            probability = math.sqrt(self.temperature) / 100.
        elif category in ['bond', 'group']:
            probability = self.intra_string_unhappiness()
        elif category == 'replacement' and self.unreplaced_objects():
            probability = 100
        elif category == 'correspondence':
            probability = self.inter_string_unhappiness()
        elif category == 'rule' and self.rule:
            probability = self.rule.total_weakness()
        elif category == 'rule':
            probability = 100
        elif category == 'translated_rule' and self.rule:
            probability = 100
        
        return probability / 100.

    def post_codelet_number(self, category):
        '''
        Return the number of codelets looking for the structure given by
        category that should be posted.
        '''
        number = 0
        case = {'few': 1, 'medium': 2, 'many': 3}
        if category == 'description':
            number = 1
        elif category == 'bond':
            number = case[self.rough_number_of_unrelated_objects()]
        elif category == 'group' and self.bonds:
            number = case[self.rough_number_of_ungrouped_objects()]
        elif category == 'replacement' and self.rule:
            number = case[self.rough_number_of_unreplaced_objects()]
        elif category == 'correspondence':
            number = case[self.rough_number_of_uncorresponding_objects()]
        elif category == 'rule':
            number = 2
        elif category == 'translated_rule' and self.rule:
            number = 1
        
        return number

    def bottom_up_codelets(self):
        '''
        Returns various bottom up codelets, with urgency and number based on
        how many of each type of codelet is needed.
        '''
        def test(category, name, urgency):
            '''
            Based on the category sent in, test for the probability for the
            codelet related to that category to be posted.  If the test does
            succeed, the number of each codelet to return is determined based
            on category.
            '''
            codelets = []
            probability = self.post_codelet_probability(category)
            number = self.post_codelet_number(category)
            if util.flip_coin(probability):
                for i in range(number):
                    codelets.append(Codelet(name, urgency=urgency))
            return codelets

        return \
        test('description', 'bottom_up_description_scout', 30) +\
        test('bond', 'bottom_up_bond_scout', 30) +\
        test('group', 'group_scout__whole_string', 30) +\
        test('replacement', 'replacement_finder', 30) +\
        test('correspondence', 'bottom_up_correspondence_scout', 30) +\
        test('correspondence', 'important_object_correspondence_scout', 30) +\
        test('rule', 'rule_scout', 30) +\
        test('translator_rule', 'rule_translator',
                30 if self.temperature > 25 else 60) +\
        [Codelet('breaker', urgency=0)]

    def objects(self):
        return self.initial_string.objects() + self.target_string.objects()

    def unreplaced_objects(self):
        unreplaced_objects = []
        for letter in self.initial_string.letters:
            if letter.replacement == None:
                unreplaced_objects.append(letter)
        return unreplaced_objects

    def structures(self):
        structures = self.bonds() + self.groups() + self.correspondences()
        if self.rule:
            return structures + [self.rule]
        else:
            return structures

    def bonds(self):
        return self.initial_string.bonds() + self.target_string.bonds()

    def groups(self):
        return self.initial_string.groups() + self.target_string.groups()

    def correspondences(self):
        return util.flatten(self._correspondences)

    def unrelated_objects(self):
        unrelated_objects = []
        for object in self.objects():
            if not object.spans_whole_string() and object.group == None:
                number_of_bonds = len(object.incoming_bonds) + len(object.outgoing_bonds)
                if object.is_leftmost_in_string() or object.is_rightmost_in_string():
                    if number_of_bonds == 0: unrelated_objects.append(object)
                else:
                    if number_of_bonds < 2: unrelated_objects.append(object)
        return unrelated_objects

    def ungrouped_objects(self):
        ungrouped_objects = []
        for object in self.objects():
            if not object.spans_whole_string() and object.group == None:
                ungrouped_objects.append(object)
        return ungrouped_objects

    def ungrouped_bonds(self):
        ungrouped_bonds = []
        for bond in self.bonds():
            if bond.from_object.group == None or bond.to_object.group == None:
                ungrouped_bonds.append(bond)
        return ungrouped_bonds

    def unreplaced_objects(self):
        unreplaced_objects = []
        for letter in self.initial_string.letters:
            if letter.replacement == None:
                unreplaced_objects.append(letter)
        return unreplaced_objects

    def uncorresponding_objects(self):
        uncorresponding_objects = []
        for object in self.objects():
            if object.correspondence == None:
                uncorresponding_objects.append(object)
        return uncorresponding_objects

    def rough_number_of_unrelated_objects(self):
        number_of_unrelated_objects = len(self.unrelated_objects())
        if number_of_unrelated_objects < util.blur(2):
            return 'few'
        elif number_of_unrelated_objects < until.blur(4):
            return 'medium'
        else:
            return 'many'

    def rough_number_of_ungrouped_objects(self):
        number_of_ungrouped_objects = len(self.ungrouped_objects())
        if number_of_ungrouped_objects < util.blur(2):
            return 'few'
        elif number_of_ungrouped_objects < until.blur(4):
            return 'medium'
        else:
            return 'many'

    def rough_number_of_unreplaced_objects(self):
        number_of_unreplaced_objects = len(self.unreplaced_objects())
        if number_of_unreplaced_objects < util.blur(2):
            return 'few'
        elif number_of_unreplaced_objects < until.blur(4):
            return 'medium'
        else:
            return 'many'

    def rough_number_of_uncorresponding_objects(self):
        number_of_uncorresponding_objects = len(self.uncorresponding_objects())
        if number_of_uncorresponding_objects < util.blur(2):
            return 'few'
        elif number_of_uncorresponding_objects < until.blur(4):
            return 'medium'
        else:
            return 'many'

    def total_unhappiness(self):
        # TODO: implement.
        return 30

    def intra_string_unhappiness(self):
        # TODO: implement.
        return 30

    def inter_string_unhappiness(self):
        # TODO: implement.
        return 30

    def structure_vs_structure(self, structure1, weight1, structure2, weight2):
        '''
        Choose probabilistically between the two structures based on strengths
        and the given weights.  Return True if structure1 wins and False if
        structure2 wins.
        '''
        structure1.update_strength_values()
        structure2.update_strength_values()
        strengths = [structure1.total_strength() * weight1,
                     structure2.total_strength() * weight2]
        adjusted_strengths = self.temperature_adjusted_values(strengths)
        return [True, False][util.weighted_index(adjusted_strengths)]

    def fight_it_out(self, structure, structure_weight, others, others_weight):
        '''
        Choose probabilistically between the structure and the other structures
        using the method structure_vs_structure.  Return True if the structure
        wins.
        '''
        for competition in others:
            if not self.structure_vs_structure(structure, structure_weight,
                                               competition, other_weight):
                return False
        return True

    def build_rule(self, rule):
        self.rule = rule
        self.activate_from_workspace_rule_descriptions(rule)

    def build_translated_rule(self, translated_rule):
        self.translated_rule = translated_rule

    def break_rule(self, rule):
        '''
        Break the rule. The only reason this function has an argument is so
        that it matchs the form of the other "break" functions and thus the
        break codelets that call it.
        '''
        self.rule = None

    def propose_rule(i_object, i_description, m_object, m_description):
        '''
        Create a proposed rule and post a rule strength tester codelet with
        urgency a function of the degree of conceptual depth of the
        descriptions in the rule.
        '''
        if not i_object:
            proposed_rule = Rule(None, None, None, None, None)
        else:
            obj_category = self.slipnet.plato_object_category
            if isinstance(m_description, ExtrinsicDescription):
                proposed_rule = Rule(i_object.get_descriptor(obj_category),
                                     i_description.description_type,
                                     i_description.descriptor,
                                     m_object.get_descriptor(obj_category),
                                     m_description.description_type_related,
                                     m_description.relation)
            else:
                proposed_rule = Rule(i_object.get_descriptor(obj_category),
                                     i_description.description_type,
                                     i_description.descriptor,
                                     m_object.get_descriptor(obj_category),
                                     m_description.description_type,
                                     m_description.descriptor)

        if not i_description:
            urgnecy = 100
        else:
            a = util.average([i_description.conceptual_depth(),
                              m_description.conceptual_depth()])
            b = a / 100.0
            urgnecy = math.sqrt(b) * 100

        return Codelet('rule_strength_tester', (proposed_rule, urgency))

    def activate_from_workspace_rule_descriptions(self, rule):
        if rule.descriptor1:
            rule.descriptor1.activate_from_workspace()
        if rule.expresses_relation():
            rule.relation.activate_from_workspace()
        else:
            if rule.descriptor2:
                rule.descriptor2.activate_from_workspace()

    # Codelet methods.
    def bond_builder(self, bond):
        '''
        Attempts to build the proposed bond, fighting with competitiors if
        necessary.
        '''
        string = bond.string
        from_object = bond.from_object
        to_object = bond.to_object

        # Make sure these objects still exist.
        objects = self.objects()
        if (from_object not in objects) or (to_object not in objects):
            return

        # Make sure the bond does not exist.
        existing_bond = string.is_bond_present(bond)
        if existing_bond:
            existing_bond.bond_category.buffer += self.activation
            if existing_bond.direction_category:
                existing_bond.direction_category.buffer += self.activation
            string.delete_proposed_bond(bond)
            return

        # Remove the proposed bond from the list of proposed bonds.
        string.delete_proposed_bond(bond)

        # Fight any incompatible bonds.
        incompatible_bonds = bond.incompatible_bonds()
        if incompatible_bonds:
            if not self.fight_it_out(bond, 1, incompatible_bonds, 1):
                return

        # Try to break any groups shared by from_object and to_object.
        incompatible_groups = from_object.common_groups(to_object)
        if incompatible_groups:
            if  not self.fight_it_out(bond, 1, incompatible_groups,
                max([group.letter_span() for group in incompatible_groups])):
                return

        # Try to break any incompatible correspondences.
        if bond.direction_category and (bond.is_leftmost_in_string() or \
                                        bond.is_rightmost_in_string()):
            incompatible_correspondences = bond.incompatible_correspondences()
            if incompatible_corresondences:
                if not self.fight_it_out(bond, 2,
                                         incompatible_correspondences, 3):
                    return

        # Break incompatible bonds, if any.
        if incompatible_bonds:
            for bond in incompatible_bonds:
                self.break_bond(bond)

        # Break incompatible groups, if any.
        if incompatible_groups:
            for group in incompatible_groups:
                self.break_group(group)

        # Break incompatible correspondences, if any.
        if incompatible_correspondences:
            for correrspondence in incompatible_correspondences:
                self.break_correspondence(correspondence)

        # Build the new bond.
        self.build_bond(bond)

    def bond_strength_tester(self, bond):
        '''
        Calculates the proposed bond's strength and decides probabilistically
        wheither or not to post a bond builder codelet with urgency as a
        function of the strength.
        '''
        # Update the strength values for the bond.
        bond.update_strength_values()
        strength = description.total_strength()

        # Decide whether or not to post the bond builder codelet.
        probability = strength / 100.0
        probability = self.temperature_adjusted_probability(probability)
        if not util.flip_coin(probability):
            bond.string.delete_proposed_bond(bond)
            return

        # Add activation to some relevant descriptions.
        bond.from_object_descriptor.buffer += self.activation
        bond.to_object_descriptor.buffer += self.activation
        bond.bond_facet.buffer += self.activation

        # Change bond's proposal level.
        bond.proposal_level = 2

        return [Codelet('bond_builder', (bond,), strength)]
        
    def bottom_up_correspondence_scout(self):
        '''
        Chooses two objects, one from the initial string and one from the
        target string, probabilistically by inter string salience. Finds all
        concept mappings between nodes at most one link away. If any concept
        mappings can be made between distinguishing descriptors, propoes a
        correspondence between the two objects, including all the concept
        mappings. Posts a correspondence strength tester codelet with urgency
        a funcion of the average strength of the distinguishing concept
        mappings.
        '''
        # Choose two objects.
        object1 = self.initial_string.choose_object('inter_string_salience')
        object2 = self.target_string.choose_object('inter_string_salience')

        # If one object spans the whole string and the other does not, fizzle.
        if object1.spans_whole_string() != object2.spans_whole_string():
            return

        # Get the possible concept mappings.
        mappings = self.concept_mappings(object1, object2,
                                         object1.relevant_descriptions(),
                                         object2.relevant_descriptions())
        if not mappings:
            return

        # Decide whether or not to continue based on slippability.
        possible = False
        for mapping in mappings:
            probability = mapping.slippablity() / 100.0
            probability = self.temperature_adjusted_probability(probability)
            if util.flip_coin(probability):
                possible = True
        if not possible:
            return

        # Check if there are any distinguishing mappings.
        distinguished_mappings = [m.distinguishing() for m in mappings]
        if not distinguished_mappings:
            return

        # If both objects span the strings, check if description needs flipped.
        possible_opposite_mappings = []
        for mapping in distinguishing_mappings:
            description_type = mapping.description_type1
            if description_type != 'plato_string_position_category' and \
               description_type != 'plato_bond_facet':
                   possible_opposite_mappings.append(mapping)

        opposite_descriptions = [m.description_type1 for m in mappings]
        if all([object1.string_spanning_group(),
                object2.string_spanning_group(),
                # FIXME: not plato_opposite.is_active(),
                self.all_opposite_concept_mappings(possible_opposite_mappings),
                'plato_direction_category' in opposite_descriptions]):
            old_object2_string_number = object2.string_number
            object2 = object2.flipped_version()
            object2.string_number = old_object2_string_number
            mappings = self.concept_mappings(object1, object2,
                                             object1.relevant_descriptions(),
                                             object2.relevant_descriptions())

        return self.propose_correspondence(object1, object2, mappings, True)

    def bottom_up_description_scout(self):
        '''
        Chooses an object probabilistically by total salience and chooses a
        relevant description of the object probabilistically by activation.
        If the description has any "has property" links that are short enough,
        chooses one of the properties probabilistically based on degree of
        association and activation. Then proposes a description based on the
        property and posts a description strength tester codelet with urgency
        a function of the activation of the property.
        '''
        # Choose an object.
        object = self.workspace.choose_object('total_salience')

        # Choose a relevant description of the object.
        description = object.choose_relevant_description_by_activation()
        if not description:
            return
        descriptor = description.descriptor

        # Check for short enough "has property" links.
        links = descriptor.similar_has_property_links()
        if not links:
            return

        # Choose a property by degree of association and activation.
        associations = [link.degree_of_association() for link in links]
        activations = [link.to_node().activation for link in links]
        choices = map(lambda a, b: a * b, associations, activations)
        index = util.select_list_position(choices)
        property = links[index].to_node()
        
        # Propose the description.
        return self.propose_description(object, property.category(), property)

    def breaker(self):
        '''
        Chooses a structure at random and decides whether or not to break it
        as a function of its total weakness.
        '''
        # Probabilistically fizzle based on temperature.
        if util.flip_coin((100.0 - self.temperature) / 100.0):
            return

        # Choose a structure at random.
        structure = random.choice(self.structures())
        if not structure:
            return

        # If the structure is a bond in a group, have to break the group first.
        if isinstance(structure, Bond) and structure.group:
            structures = [structure, structure.group]
        else:
            structures = [structure]

        # See if the structures can be broken.
        for structure in structures:
            probability = structure.total_weakness() / 100.0
            probability = self.temperature_adjusted_probability(probability)
            if not util.flip_coin(probability):
                return

        # Break the structures.
        for structure in structues:
            if isinstance(structure, Bond):
                self.break_bond(structure)
            elif isinstance(structure, Group):
                self.break_group(structure)
            elif isinstance(structure, Correspondence):
                self.break_correspondence(structure)

    def correspondence_builder(self, correspondence, flip_object2):
        '''
        Attempts to build the proposed correspondence, fighting it out with
        competitors if necessary.
        '''
        object1 = correspondence.object1
        object2 = correspondence.object2
        flipped = object2.flipped_version()
        existing_object2_group = self.target_string.group_present(flipped)

        # If the objects do not exist anymore, then fizzle.
        objects = self.objects()
        if (object1 not in objects) or \
            ((object2 not in objects) and \
            (not (flip_object2 and existing_object2_group))):
            return

        # If the correspondence exists, add and activiate concept mappings.
        existing_correspondence = self.correspondence_present(correspondence)
        if existing_correspondence:
            self.delete_proposed_correspondence(correspondence)
            labels = [m.label for m in correspondence.concept_mappings]
            for label in labels:
                label.buffer += self.activation
            mappings_to_add = []
            for mapping in correspondence.concept_mappings:
                if not correspondence.mapping_present(mapping):
                    mappings_to_add.append(mapping)
            existing_correspondence.add_concept_mappings(mappings_to_add)
            return

        # If any concept mappings are no longer relevant, then fizzle.
        for mapping in correspondence.concept_mappings:
            if not mapping.relevant:
                return

        # Remove the proposed correpondence from proposed correspondences.
        self.delete_proposed_correspondence(correspondence)

        # The proposed correspondence must win against all incompatible ones.
        incompatible_correspondences = correspondence.incompatible_corresondences()
        for incompatible_correspondence in incompatible_correspondences:
            if not self.fight_it_out(correspondence,
                                     correspondence.letter_span,
                                     [incompatible_correspondence],
                                     incompatible_correspondence.letter_span):
                return

        # The proposed correspondence must win against any incompatible bond.
        if (object1.leftmost_in_string or object1.rightmost_in_string) and \
               (object2.leftmost_in_string or object2.rightmost_in_string):
            incompatible_bond = correspondence.incompatible_bond()
            if incompatible_bond:
                if not self.fight_it_out(correspondence, 3,
                                         [incompatible_bond], 2):
                    return
                # If the bond is in a group, fight against it as well.
                incompatible_group = incompatible_bond.group
                if incompatible_group:
                    if not self.fight_it_out(correspondence, 1,
                                             [incompatible_group], 1):
                        return

        # If the desired object2 is flipped its existing group.
        if flip_object2:
            if not self.fight_it_out(correspondence, 1,
                                     [existing_object2_group], 1):
                return

        # The proposed corresondence must win against an incompatible rule.
        incompatible_rule = correspondence.incompatible_rule()
        if incompatible_rule:
            if not self.fight_it_out(correspondence, 1, [self.rule], 1):
                return

        # Break all incompatible structures.
        if incompatible_correspondences:
            for incompatible_correspondence in incompatible_correspondences:
                self.break_correspondence(incompatible_correspondence)

        if incompatible_bond:
            self.break_bond(incompatible_bond)

        if incompatible_group:
            self.break_group(incompatible_group)

        if existing_object2_group:
            self.break_group(existing_object2_group)
            for bond in existing_object2_group.bonds():
                self.break_bond(bond)
            for bond in object2.bonds():
                self.build_bond(bond)
            self.build_group(object2)

        if incompatible_rule:
            self.break_rule(self.rule)

        # Build the correspondence.
        self.build_correspondence(correspondence)

    def correspondence_strength_tester(self, correspondence, flip_object2):
        '''
        Calculates the proposed correspondence's strength and probabilistically
        decides whether or not to post a correspondence builder codelt with
        urgency a function of the strength.
        '''
        object1 = correspondence.object1
        object2 = correspondence.object2
        flipped = object2.flipped_version()

        # If the objects do not exist anymore, then fizzle.
        objects = self.objects()
        if (object1 not in objects) or \
            ((object2 not in objects) and \
            (not (flip_object2 and self.target_string.group_present(flipped)))):
            return

        # Calculate the proposed correspondence's strength.
        correspondence.update_strength_values()
        stength = correspondence.total_strength()

        # Decide whether to post a corresondpondence builder codelet or not.
        probability = strength / 100.0
        probability = self.temperature_adjusted_probability(probability)
        if not util.flip_coin(probability):
            self.delete_proposed_correspondenc(correspondence)
            return

        # Add some activation to some descriptions.
        for mapping in correspondence.concept_mappings:
            mapping.description_type1.buffer += self.activation
            mapping.descriptor1.buffer += self.activation
            mapping.description_type2.buffer += self.activation
            mapping.descriptor2.buffer += self.activation

        # Set correspondence proposal level.
        correspondence.proposal_level = 2

        # Post the correspondence builder codelet.
        return [Codelet('correspondence_buidler',
                        (correspondence, flip_object2), strength)]

    def description_builder(self, description):
        '''
        Attempts to build the proposed description. If it already exists, its
        activations are boosted.
        '''
        # Make sure the object still exists.
        if description.object not in self.objects():
            return

        # Make sure the description does not exist.
        if description in description.object.descriptions():
            description.description_type.buffer += self.activation
            description.descriptor.buffer += self.activation
            return

        # Build the description.
        self.build_description(description)

    def description_strength_tester(self, description):
        '''
        Calculates the proposed descriptions's strength and probabilistically
        decides whether or not to post a description builder codelet with
        urgency as a function of the strength.
        '''
        # Activate the descriptor.
        description.descriptor.buffer += self.activation

        # Update the strength values for the description.
        description.update_strength_values()
        strength = description.total_strength()

        # Decide whether or not to post the description builder codelet.
        probability = strength / 100.0
        probability = self.temperature_adjusted_probability(probability)
        if not util.flip_coin(probability):
            return
        
        return [Codelet('description_builder', (description,), strength)]

    def group_builder(self, group):
        '''
        Tries to build the proposed group, fighting with any competitors.
        '''
        string = group.string

        # Make sure this group doesn't already exist.
        existing_group = string.group_present(group)
        if existing_group:
            for description in existing_group.descriptions:
                description.desriptor.buffer += self.activation
            for description in group.descriptions:
                if not existing_group.description_present(description):
                    new_description = Description(existing_group,
                                                  description.description_type,
                                                  description.descriptor)
                    self.build_description(new_description)
            string.delete_proposed_group(group)
            return

        # Make sure all bonds or their flipped versions are still there.
        all_bonds_exist = True
        for bond in group.bonds():
            flipped = bond.flipped_version()
            if not (string.bond_present(bond) or string.bond_present(flipped)):
                all_bonds_exist = False
                break
        if not all_bonds_exist:
            string.delete_proposed_group(group)
            return

        # Take the proposed group off the list of proposed groups.
        string.delete_proposed_group(group)

        # Check if any bonds need to be flipped and fight if so.
        bonds_to_flip = group.bonds_to_be_flipped()
        if bonds_to_flip:
            result = self.fight_it_out(group, group.letter_span,
                                       bonds_to_flip, 1)
            if not result:
                return

        # Fight any incompatible groups.
        incompatible_groups = group.incompatible_groups()
        for incompatible_group in incompatible_groups:
            if (group.group_category == incompatible_group.group_category) and\
            (group.direction_category == incompatible_group.direction_category):
                group_weight = group.length
                incompatible_weight = incompatible_group.length
            else:
                group_weight = 1
                incompatible_weight = 1
            result = self.fight_it_out(group, group_weight,
                                       incompatible_group, incompatible_weight)
            if not result:
                return

        # Fight any incompatible correspondences.
        incompatible_correspondences = group.incompatible_correspondences()
        if group.direction_category and incompatible_correspondences:
            result = self.fight_it_out(group, 1,
                                       incompatible_correspondences, 1)
            if not result:
                return

        # Break incompatible groups.
        for incompatible_group in incompatible_groups:
            self.break_group(incompatible_group)

        # Flip any bonds that need it and replace any bonds that were rebuilt.
        new_bonds = []
        if bonds_to_flip:
            for bond in group.bonds():
                flipped_bond = string.bond_present(bond.flipped_version())
                if flipped_bond:
                    self.break_bond(flipped_bond)
                    self.build_bond(bond)
                    new_bonds.append(bond)
                else:
                    existing_bond = string.bond_present(bond)
                    if existing_bond != bond:
                        new_bonds.append(existing_bond)
                    else:
                        new_bonds.append(bond)
        # FIXME: Actually replacing the bonds is not in the copycat source.
        #group.bonds = new_bonds

        # Break incompatible correspondences.
        for incompatible_correspondence in incompatible_correspondences:
            self.break_correspondence(incompatible_correspondence)

        # Build the group.
        self.build_group(group)

    def group_scout__whole_string(self):
        '''
        Tries to make a group out of the entire string. If possible, makes a
        proposed string spanning group and posts a group strength tester
        codelet with urgency a function of the degree of association of bonds
        of the given bond category.
        '''
        string = self.random_string()

        # Choose a salient leftmost object and get objects and bonds.
        if not string.bonds():
            return
        left_object = string.choose_leftmost_object()
        next_bond = left_object.right_bond
        objects = [left_object]
        bonds = []
        while next_bond:
            bonds.append(next_bond)
            next_object = next_bond.right_object
            objects.append(next_object)
            next_bond = next_object.right_bond
        right_object = next_object
        if (not bonds) or (not right_object.rightmost_in_string()):
            return

        # Choose a random bond and try making a group based on it.
        bond = random.choice(bonds)
        bond_category = bond.bond_category
        direction_category = bond.direction_category
        facet = bond.bond_facet
        bonds = self.possible_group_bonds(bond_category, direction_category,
                                          facet, bonds)
        if not bonds:
            return

        group_category = bond_category.related_node(plato_group_category)

        return self.propose_group(objects, bonds, group_category,
                                  direction_category)

    def group_strength_tester(self, group):
        '''
        Calculates the proposed group's strength and probabilistically decides
        whether or not to post a group builder codelet with urgency a function
        of the strength.
        '''
        # Calculate the group's stength.
        group.update_strength_values()
        stength = group.total_stength()

        # Decide whether or not to post the group builder codelet.
        probability = strength / 100.0
        probability = self.temperature_adjusted_probability(probability)
        if not util.flip_coin(probability):
            group.string.delete_proposed_group(group)
            return

        # Add some activation to descriptions.
        group.bond_category.buffer += self.activation
        if group.direction_category:
            group.direction_category.buffer += self.activation

        # Set group's proposal level.
        group.proposal_level = 2

        return Codelet('group_builder', (group,), strength)

    def important_object_correspondence_scout(self):
        '''
        Chooses an object from the initial string probabilistically based on
        importance. Picks a description of the object probabilistically and
        looks for an object in the target string with the same description,
        modulo the appropriate slippage, if any of the slippages currently in
        the workspace apply. Then finds all concept mappings between nodes at
        most one link away. Makes a proposed correspondence between the two
        objects, including all the concept mappings. Posts a correspondence
        strength tester codelet with urgency a function of the average
        strength of the distinguishing concept mappings.
        '''
        # Choose an object.
        object1 = self.initial_string.choose_object('relative_importance')

        # Choose a description by conceptual depth.
        object1_description = object1.choose_relative_distinguishing_description_by_conceptual_depth()
        if not object1_description:
            return
        object1_descriptor = object1_description.descriptor

        # Find the corresponding object2_descriptor.
        object2_descriptor = object1_descriptor
        for slippage in self.slippages:
            if slippage.descriptor1 == object1_descriptor:
                object2_descriptor = slippage.descriptor2

        # Find an object with that descriptor in the target string.
        object2_candidates = []
        for object in self.target_string.objects():
            for description in object.relevant_descriptions():
                if description.descriptor == object2_descriptor:
                    object2_candidates.append(object)
        if not object2_candidates:
            return
        values = [obj.inter_string_salience() for obj in object2_candidates]
        index = util.select_list_position(values)
        object2 = object2_candidates[index]

        # If one object spans the whole string and the other does not, fizzle.
        if object1.spans_whole_string() != object2.spans_whole_string():
            return

        # Get the possible concept mappings.
        mappings = self.concept_mappings(object1, object2,
                                         object1.relevant_descriptions(),
                                         object2.relevant_descriptions())
        if not mappings:
            return

        # Decide whether or not to continue based on slippability.
        possible = False
        for mapping in mappings:
            probability = mapping.slippablity() / 100.0
            probability = self.temperature_adjusted_probability(probability)
            if util.flip_coin(probability):
                possible = True
        if not possible:
            return

        # Check if there are any distinguishing mappings.
        distinguished_mappings = [m.distinguishing() for m in mappings]
        if not distinguished_mappings:
            return

        # If both objects span the strings, check if description needs flipped.
        possible_opposite_mappings = []
        for mapping in distinguishing_mappings:
            description_type = mapping.description_type1
            if description_type != 'plato_string_position_category' and \
               description_type != 'plato_bond_facet':
                   possible_opposite_mappings.append(mapping)

        opposite_descriptions = [m.description_type1 for m in mappings]
        if all([object1.string_spanning_group(),
                object2.string_spanning_group(),
                # FIXME: not plato_opposite.is_active(),
                self.all_opposite_concept_mappings(possible_opposite_mappings),
                'plato_direction_category' in opposite_descriptions]):
            old_object2_string_number = object2.string_number
            object2 = object2.flipped_version()
            object2.string_number = old_object2_string_number
            mappings = self.concept_mappings(object1, object2,
                                             object1.relevant_descriptions(),
                                             object2.relevant_descriptions())

        return self.propose_correspondence(object1, object2, mappings, True)

    def replacement_finder(self):
        '''
        Chooses a letter at random in the initial string. Checks if it is the
        changed leter and marks it as changed. Adds a description of the 
        relation describing the change if there is one. Can only deal with
        letters changing into letters, not letters changing into groups or
        vice versa.
        '''
        i_letter = self.initial_string.random_letter()
        if i_letter.replacement:
            return

        m_letter = self.modified_string.letter(i_letter.left_string_position)

        # Check if m_letter's letter_category is different form i_letter's.
        i_letter_category = i_letter.get_descriptor(plato_letter_category)
        m_letter_category = m_letter.get_descriptor(plato_letter_category)
        if i_letter_category != m_letter_category:
            i_letter.changed = True
            # FIXME: Another example of needing slipnet information.
            change_relation = slipnet.label_node(i_letter_category,
                                                 m_letter_category)
            if change_relation:
                description = ExtrinsicDescription(change_relation,
                                                   plato_letter_category,
                                                   i_letter)
                m_letter.add_extrinsic_description(description)

        replacement = Replacement(i_letter, m_letter)
        self.add_replacement(replacement)
        i_letter.replacement = replacement

    def rule_builder(self, rule):
        '''
        Tries to build the proposed rule, fighting with competitors as needed.
        '''
        # Make sure this rule doesn't already exist.
        if self.rule == rule:
            rule.activate_descriptions_from_workspace(rule, self.activation)
            return

        # Fight an existing rule.
        if self.rule:
            result = self.fight_it_out(rule, 1, self.rule, 1)
            if not result:
                return

        # Build the rule.
        if self.rule:
            self.break_rule(self.rule)
        self.build_rule(rule)

    def rule_scout(self):
        '''
        Fills in the rule template, "Replace _____ by _____". To do this, it
        chooses descriptions of the changed object in the initial string and
        the object in the modified string that replaces it. If a rule can be
        made, it is proposed, and a rule strength tester codelet is posted with
        urgency a function of the degree of conceptual depth of the chosen
        descriptions.
        '''
        # If not all replacements have been found, then fizzle.
        if self.null_replacement():
            return

        # Find changed object.
        changed_objects = []
        for object in self.initial_string.objects():
            if object.changed():
                changed_objects.append(object)

        # If there is more than one changed object signal an error and quit.
        if len(changed_objects) > 1:
            print "Can't solve problems with more than one letter changed."
            sys.exit()

        # If not changed object, propose rule specifying no changes.
        if not changed_objects:
            self.propose_rule(None, None, None, None)
            return

        i_object = changed_objects[0]
        m_object = i_object.replacement.object2

        # Get all relevant distinguishing descriptions.
        if not i_object.correspondences:
            i_descriptions = i_object.rule_initial_string_descriptions
        else:
            correspondence_slippages = i_object.correspondence.slippages
            i_descriptions = []
            for description in i_object.rule_initial_string_descriptions:
                # FIXME: Where is this defined?
                applied_slippages = description.apply_slippages(i_object,
                        correspondence_slippages)
                relevant_descriptions = i_object.correspondence.object2.relevant_descriptions()
                if description_member(applied_slippages, relevant_descriptions):
                    i_descriptions.append(description)
        if not i_descriptions:
            return

        # Choose the descriptior for the initial string object.
        depths = [desription.conceptual_depth for description in i_descriptions]
        i_probabilities = self.temperature_adjusted_values(depths)
        index = util.select_list_position(i_probabilities)
        i_description = i_descriptions[index]

        # Choose the descriptor for the modified string object.
        m_descriptions = m_object.extrinsic_descriptions() + \
                         m_object.rule_modified_string_descriptions()
        if not m_descriptions:
            return
        depths = [desription.conceptual_depth for description in m_descriptions]
        m_probabilities = self.temperature_adjusted_values(depths)
        index = util.select_list_position(m_probabilities)
        m_description = m_descriptions[index]

        # Kludge to avoid rules like "Replace C by succesor of C".
        relation = m_description.relatino
        related_descriptor = i_description.descriptor.related_node(relation)
        if isinstance(m_description, ExtrinsicDescription) and \
                related_descriptor:
            for description in m_object.descriptions:
                if description.descriptor == related_descriptor:
                    m_desription = description
                    break

        # Propose the rule.
        self.propose_rule(i_object, i_description, m_object, m_description)

    def rule_strength_tester(self, rule):
        '''
        Calculates the proposed rule's strength and probabilistically decides
        whether or not to post a rule builder codelet with urgency a fucntion
        for its strength.
        '''
        # Calculate strength.
        rule.update_strength_values()
        strength = rule.total_strength()

        # Decide whether or not to post a rule builder codelet.
        probability = strength / 100.0
        probability = self.temperature_adjusted_probability(probability)
        if not util.flip_coin(probability):
            return

        return Codelet('rule_builder', (rule,), strength)

    def rule_translator(self):
        '''
        Translate the rule according to the translation rules given in the
        slippages on the workspace.
        '''
        # Make sure there is a rule.
        if not self.rule:
            return
        if self.rule.no_change:
            self.translated_rule = NonRelationRule(None, None, None,
                                                   None, None, None)
            return

        # If the temperature is too high, fizzle.
        threshold = self.answer_temperature_threshold_distribution.choose()
        if self.temperature > threshold:
            return

        # Build the translation of the rule.
        changed_object = None
        for object in self.initial_string.objects():
            if object.changed:
                changed_object = object
                break
        if not changed_object:
            return

        changed_object_correspondence = changed_object.correspondence

        # Get the slippages to use.
        slippages = self.slippages
        if changed_object_correspondence:
            for slippage in self.slippages:
                for mapping in changed_object_correspondence.concept_mapptings:
                    if self.contradictory_concept_mappings(mapping, slippage):
                        slippages.remove(slippage)

        rule = self.rule
        if rule.relation():
            args = []
            for arg in [rule.object_category1, rule.descriptor1_face,
                        rule.descriptor1, rule.object_category2,
                        rule.replaced_description_type, rule.relation]:
                args.append(arg.apply_slippages(slippages))
                translated_rule = RelationRule(*args)
        else:
            args = []
            for arg in [rule.object_category1, rule.descriptor1_facet,
                        rule.descriptor1, rule.object_category2,
                        rule.replaced_description_type, rule.descriptor2]:
                args.append(arg.apply_slippages(slippages))
                translated_rule = NonRelationRule(*args)

        self.build_translated_rule(translated_rule)

    def top_down_bond_scout__category(self, category):
        '''
        Chooses a string probabilistically by the relevance of the category in
        the string and the string's unhappiness. Chooses an object and a
        neighbor of the object in the string probabilistically by instra
        string salience. Chooses a bond facet probabilistically by relevance
        in the string. Checks if there is a bond of the category between the
        two descriptors of the facet, posting a bond strength tester codelet
        with urgency a function of the degree of association of bonds of the
        category.
        '''
        # Choose a string.
        initial_string = self.initial_string
        target_string = self.target_string
        i_relevance = initial_string.local_bond_category_relevance(category)
        t_relevance = target_string.local_bond_category_relevance(category)
        i_unhappiness = initial_string.intra_string_unhappiness()
        t_unhappiness = target_string.intra_string_unhappiness()
        values = [round(util.average(i_relevance, i_unhappiness)),
                  round(util.average(t_relevance, t_unhappiness))]
        index = util.select_list_position(values)
        string = [initial_string, target_string][index]

        # Choose an object and neighbor.
        object = string.choose_object('intra_string_salience')
        neighbor = object.choose_neighbor()
        if not neighbor:
            return

        # Choose bond facet.
        facet = object.choose_bond_facet(neighbor)
        if not facet:
            return

        # Get the descriptors of the facet if they exist.
        object_descriptor = object.descriptor(facet)
        neighbor_descriptor = neighbor.descriptor(facet)
        if (not object_descriptor) or (not neighbor_descriptor):
            return

        # Check for a possible bond.
        if object_descriptor.bond_category(neighbor_descriptor) == category:
            from_object = object
            to_object = neighbor
            from_descriptor = object_descriptor
            to_descriptor = neighbor_descriptor
        elif neighbor_descriptor.bond_category(object_descriptor) == category:
            from_object = neighbor
            to_object = object
            from_descriptor = neighbor_descriptor
            to_descriptor = object_descriptor
        else:
            return

        # Propose the bond.
        return self.propose_bond(from_object, to_object, category, facet,
                                 from_descriptor, to_descriptor)

    def top_down_bond_scout__direction(self, category):
        '''
        Chooses a string probabilistically by the relevance of the direction
        category in the string and the string's unhappiness. Chooses an object
        in the string probabilisitically by intra string salience. Chooses a
        neighbor of the object in the given direction. Chooses a bond facet
        probabilistically by relevance in the string. Checks if there is a
        bond of the given direction between the two descriptors of the facet,
        posting a bond strength tester codelet with urgency a function of the
        degree of association of bonds of the bond category.
        '''
        # Choose a string.
        initial_string = self.initial_string
        target_string = self.target_string
        i_relevance = initial_string.local_direction_category_relevance(category)
        t_relevance = target_string.local_direction_category_relevance(category)
        i_unhappiness = initial_string.intra_string_unhappiness()
        t_unhappiness = target_string.intra_string_unhappiness()
        values = [round(util.average(i_relevance, i_unhappiness)),
                  round(util.average(t_relevance, t_unhappiness))]
        index = util.select_list_position(values)
        string = [initial_string, target_string][index]

        # Choose an object and neighbor.
        object = string.choose_object('intra_string_salience')
        if category.name == 'plato_left':
            neighbor = object.choose_left_neighbor()
        elif category.name == 'plato_right':
            neighbor = object.choose_right_neighbor()
        if not neighbor:
            return

        # Choose bond facet.
        facet = object.choose_bond_facet(neighbor)
        if not facet:
            return
        
        # Get the descriptors of the facet if they exist.
        object_descriptor = object.descriptor(facet)
        neighbor_descriptor = neighbor.descriptor(facet)
        if (not object_descriptor) or (not neighbor_descriptor):
            return

        # Check for a possible bond.
        bond_category = from_descriptor.bond_category(to_descriptor)
        if (not bond_category) or (not bond_category.directed):
            return

        # Propose the bond.
        return self.propose_bond(from_object, to_object, bond_category, facet,
                                 from_descriptor, to_descriptor)

    def top_down_description_scout(self, description_type):
        '''
        Chooses an object probabilistically by total salience, checking if it
        fits any of the descriptions in the description_type's "has instance"
        list. If so, proposes a description based on the property and posts a
        description strength tester codelet with urgency a funtion of the
        activation of the proposed descriptor.
        '''
        # Choose an object.
        object = self.choose_object('total_salience')

        # Choose a relevant descriptor.
        descriptors = description_type.possible_descriptors(object)
        if not descriptors:
            return
        activations = [descriptor.activation for descriptor in descriptors]
        index = util.select_list_position(activations)
        descriptor = descriptors[index]

        # Propose the description.
        return self.propose_description(object, description_type, descriptor)

    def top_down_group_scout__category(self, category):
        '''
        Chooses an object, a direction to scan in, and a number of bonds to
        scan in that direction. The direction category of the group is the
        direction of the first bond scanned. If there are no bonds and the
        group category is not plato-same-group, the chooses a direction
        category probabilistically as a function of global and local relevance.
        Scans until no more bonds of the necessary type and direction are
        found. If possible, makes a proposed group of the given type of the
        objects scanned and posts a group length tester codelet with urgency
        a function of the degree of association of bonds of the given bond
        category.
        '''
        bond_category = category.related_node('plato_bond_category')

        # Choose a string based on local bond category relevance.
        i_string = self.initial_string
        i_relevance = i_string.local_bond_category_relevance(bond_category)
        i_unhappiness = i_string.intra_string_unhappiness()
        t_string = self.target_string
        t_relevance = t_string.local_bond_category_relevance(bond_category)
        t_unhappiness = t_string.intra_string_unhappiness()
        choices = [i_string, t_string]
        weights = [round(util.average(i_relevance, i_unhappiness)),
                   round(util.average(t_relevance, t_unhappniess))]
        string = choices[util.select_list_position(weights)]

        # Choose an object by intra string salience.
        object = string.choose_object('intra_string_salience')
        if object.spans_whole_string():
            return

        # Choose a direction in which to scan.
        # FIXME: no access to slipnodes.
        if object.leftmost_in_string():
            direction = plato_right
        elif object.rightmost_in_string():
            direction = plato_left
        else:
            activations = [plato_left.activation, plato_right.activation]
            index = util.select_list_position(activations)
            direction = [plato_left, plato_right][index]

        # Choose the number of bonds to scan.
        number = util.select_list_position(string.bonds_to_scan_distribution())

        # Get the first bond in that direction.
        if direction == plato_left:
            bond = object.left_bond
        else:
            bond = object.right_bond

        if (not bond) or (bond.bond_category != bond_category):
            if isinstance(object, Group):
                return
            objects = [object]
            bonds = []
            if category == plato_samegroup:
                possible_single_letter_group_direction = None
            else:
                choices = [plato_left, plato_right]
                weights = [node.local_descriptor_support(string, plato_group) \
                            for node in choices]
                index = util.select_list_position(weights)
                possible_single_letter_group_direction = choices[index]

            possible_single_letter_group = Group(category,
                                                 possible_single_letter_direction,
                                                 object, object, objects, bonds)

            probility = possible_possible_single_letter_group.single_letter_group_probability()
            if util.flip_coin(probability):
                return self.propose_group(objects, bonds, category,
                                          possible_single_letter_group_direction)
        
        direction_category = bond.direction_category
        facet = bond.bond_facet
        opposite_bond_category = bond_category.get_related_node(plato_opposite)
        if direction_category:
            opposite_direction_category = direction_category.get_related_node(plato_opposite)

        # Get objects and bonds.
        objects = [bond.left_object, bond.right_object]
        bonds = [bond]
        next_bond = bond
        for i in range(2, number):
            bond_to_add = None
            if direction == plato_left:
                next_bond = next_bond.choose_left_neighbor()
                if not next_bond:
                    break
                else:
                    next_object = next_bond.left_object
            else:
                next_bond = next_bond.choose_right_neighbor()
                if not next_bond:
                    break
                else:
                    next_object = next_bond.right_object

            # Decide whether or not to add bond.
            if not next_bond:
                bond_to_add = None
            elif (next_bond.bond_category == bond_category) and \
                 (next_bond.direction_category == direction_category) and\
                 (next_bond.bond_facet == facet):
                bond_to_add = next_bond
            elif (next_bond.bond_category == opposite_bond_category) and \
                 (next_bond.direction_category == opposite_direction_category) and \
                 (next_bond.bond_facet == facet):
                bond_to_add = next_bond.flipped_version()

            if bond_to_add:
                objects.append(next_object)
                bonds.append(bond_to_add)
            else:
                break

        # Propose the group.
        return self.propose_group(objects, bonds, category, direction_category)

    def top_down_group_scout__direction(self, category):
        '''
        Chooses an object, a direction to scan in, and a number of bonds to
        scan in that direction. The category of the group is the associated
        group category of the first bond scanned. Scans until no more bonds of
        the necessary type and direction are found. If possible, makes a
        proposed group of the given direction out of the objects scanned and
        posts a group strength tester codelet with urgency a function of the
        degree of association of bonds of the given bond category.
        '''
        # Choose a string based on local direction category relevance.
        i_string = self.initial_string
        i_relevance = i_string.local_direction_category_relevance(category)
        i_unhappiness = i_string.intra_string_unhappiness()
        t_string = self.target_string
        t_relevance = t_string.local_direction_category_relevance(category)
        t_unhappiness = t_string.intra_string_unhappiness()
        choices = [i_string, t_string]
        weights = [round(util.average(i_relevance, i_unhappiness)),
                   round(util.average(t_relevance, t_unhappniess))]
        string = choices[util.select_list_position(weights)]

        # Choose an object by intra string salience.
        object = string.choose_object('intra_string_salience')
        if object.spans_whole_string():
            return

        # Choose a direction in which to scan.
        # FIXME: no access to slipnodes.
        if object.leftmost_in_string():
            direction = plato_right
        elif object.rightmost_in_string():
            direction = plato_left
        else:
            activations = [plato_left.activation, plato_right.activation]
            index = util.select_list_position(activations)
            direction = [plato_left, plato_right][index]

        # Choose the number of bonds to scan.
        number = util.select_list_position(string.bonds_to_scan_distribution())

        # Get the first bond in that direction.
        if direction == plato_left:
            bond = object.left_bond
        else:
            bond = object.right_bond

        if (not bond) or (bond.direction_category != category):
            return

        bond_category = bond.bond_category
        facet = bond.bond_facet

        opposite_bond_category = bond_category.get_related_node(plato_opposite)
        opposite_category = category.get_related_node(plato_opposite)

        # Get objects and bonds.
        objects = [bond.left_object, bond.right_object]
        bonds = [bond]
        next_bond = bond
        for i in range(2, number):
            bond_to_add = None
            if direction == plato_left:
                next_bond = next_bond.choose_left_neighbor()
                if not next_bond:
                    break
                else:
                    next_object = next_bond.left_object
            else:
                next_bond = next_bond.choose_right_neighbor()
                if not next_bond:
                    break
                else:
                    next_object = next_bond.right_object

            # Decide whether or not to add bond.
            if not next_bond:
                bond_to_add = None
            elif (next_bond.bond_category == bond_category) and \
                 (next_bond.direction_category == direction_category) and \
                 (next_bond.bond_facet == facet):
                bond_to_add = next_bond
            elif (next_bond.bond_category == opposite_bond_category) and \
                 (next_bond.direction_category == opposite_direction_category) and \
                 (next_bond.bond_facet == facet):
                bond_to_add = next_bond.flipped_version()

            if bond_to_add:
                objects.append(next_object)
                bonds.append(bond_to_add)
            else:
                break

        group_category = bond_category.get_related_node(plato_group_category)

        return self.propose_group(objects, bonds, group_category, category)
