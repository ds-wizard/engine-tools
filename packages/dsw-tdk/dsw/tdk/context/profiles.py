"""Profiles of `generate-context` (WEP 24, Appendix D): how much a generated context contains."""
from __future__ import annotations

import dataclasses
import typing


PROFILES = ('empty', 'minimal', 'typical', 'full', 'edge')

VISIBILITIES = ('PrivateProjectVisibility', 'VisibleViewProjectVisibility',
                'VisibleCommentProjectVisibility', 'VisibleEditProjectVisibility')
SHARING_MODES = ('RestrictedProjectSharing', 'AnyoneWithLinkViewProjectSharing',
                 'AnyoneWithLinkCommentProjectSharing', 'AnyoneWithLinkEditProjectSharing')
#: the permission sets the backend uses, from the weakest
PERMISSION_SETS = (['VIEW'], ['COMMENT', 'VIEW'], ['COMMENT', 'EDIT', 'VIEW'],
                   ['ADMIN', 'COMMENT', 'EDIT', 'VIEW'])

Range = tuple[int, int]


@dataclasses.dataclass(frozen=True)
class Profile:
    name: str
    #: 'none', 'chapter' (top-level questions only), 'random' or 'all' visible questions
    replies: typing.Literal['none', 'chapter', 'random', 'all']
    reply_probability: float
    list_items: Range
    nested_list_items: Range
    #: 'one', 'subset', 'all' or 'alternate' (all in odd variants, none in even ones)
    multi_choice: typing.Literal['one', 'subset', 'all', 'alternate']
    users: Range
    groups: Range
    versions: Range
    files: Range
    #: 'none', 'first', 'random', 'last' or 'round-robin'
    phase: typing.Literal['none', 'first', 'random', 'last', 'round-robin']
    labels: Range
    project_tags: Range
    #: 'short', 'plausible' or 'edge'
    strings: typing.Literal['short', 'plausible', 'edge']
    #: 'fixed' (private, restricted), 'random' or 'round-robin'
    settings: typing.Literal['fixed', 'random', 'round-robin']
    #: rate of `--mutate`
    mutation_rate: float
    max_depth: int = 64


PROFILE_BY_NAME = {profile.name: profile for profile in (
    Profile('empty', replies='none', reply_probability=0, list_items=(0, 0),
            nested_list_items=(0, 0), multi_choice='one', users=(1, 1), groups=(0, 0),
            versions=(0, 0), files=(0, 0), phase='none', labels=(0, 0), project_tags=(0, 0),
            strings='short', settings='fixed', mutation_rate=1.0),
    Profile('minimal', replies='chapter', reply_probability=1, list_items=(1, 1),
            nested_list_items=(0, 0), multi_choice='one', users=(1, 1), groups=(0, 0),
            versions=(0, 0), files=(0, 0), phase='first', labels=(0, 0), project_tags=(0, 0),
            strings='short', settings='fixed', mutation_rate=0.5),
    Profile('typical', replies='random', reply_probability=0.7, list_items=(1, 3),
            nested_list_items=(1, 3), multi_choice='subset', users=(2, 5), groups=(0, 2),
            versions=(0, 3), files=(0, 2), phase='random', labels=(1, 3), project_tags=(1, 3),
            strings='plausible', settings='random', mutation_rate=0.2),
    Profile('full', replies='all', reply_probability=1, list_items=(3, 5),
            nested_list_items=(3, 5), multi_choice='all', users=(10, 10), groups=(3, 3),
            versions=(5, 5), files=(5, 5), phase='last', labels=(5, 8), project_tags=(5, 8),
            strings='plausible', settings='random', mutation_rate=0.1),
    Profile('edge', replies='all', reply_probability=1, list_items=(20, 25),
            nested_list_items=(2, 2), multi_choice='alternate', users=(50, 50), groups=(10, 10),
            versions=(20, 20), files=(10, 10), phase='round-robin', labels=(10, 15),
            project_tags=(10, 15), strings='edge', settings='round-robin', mutation_rate=0.3,
            max_depth=4),
)}
