import pytest

from bokkio.model import BokkioActionError, BokkioError, BokkioPermissionError
from test_cli import Element
from test_refs import make_backend


class OverflowCell(Element):
    @property
    def bounds(self):
        raise OverflowError('cannot convert float infinity to integer')

    @bounds.setter
    def bounds(self, value):
        pass


def test_virtual_cell_remains_readable_and_cannot_dispatch_after_annotation():
    cell = OverflowCell('button', 'Virtual cell', '42')
    sibling = Element('button', 'Save')
    backend = make_backend([cell, sibling])

    class Native:
        def annotate(self, tree, pid):
            tree['children'][0]['children'][0]['actions'] = ['click', 'scroll']
            return tree

    backend._native = Native()
    node = backend.find('TextEdit', 'button', 'Virtual cell')[0]
    assert node['value'] == '42'
    assert node['bounds'] is None
    assert node['state']['visible'] is False
    assert node['platform_data']['invalid_bounds'] is True
    assert node['actions'] == []
    assert backend.find('TextEdit', 'button', 'Save')[0]['actions'] == ['click']
    with pytest.raises(BokkioActionError, match='no action dispatched'):
        backend.perform('TextEdit', 'click', ref=node['ref'])
    assert cell.value == '42'


@pytest.mark.parametrize('value', [float('inf'), float('-inf'), float('nan')])
def test_raw_nonfinite_coordinates_are_not_serialized_or_actionable(value):
    cell = Element('button', 'Virtual cell')
    cell.bounds.x = value
    backend = make_backend([cell])
    node = backend.find('TextEdit', 'button')[0]
    assert node['bounds'] is None and node['actions'] == []


def test_missing_geometry_is_distinct_from_invalid_geometry():
    cell = Element('button', 'Menu command')
    cell.bounds = None
    node = make_backend([cell]).find('TextEdit', 'button')[0]
    assert node['actions'] == ['click']
    assert 'invalid_bounds' not in node['platform_data']


@pytest.mark.parametrize('message,error_type', [
    ('Accessibility Permission denied', BokkioPermissionError),
    ('provider disconnected', BokkioError),
])
def test_geometry_permission_and_provider_failures_are_not_suppressed(message, error_type):
    class Broken(OverflowCell):
        @property
        def bounds(self):
            raise RuntimeError(message)

        @bounds.setter
        def bounds(self, value):
            pass

    with pytest.raises(error_type):
        make_backend([Broken('button', 'Broken')]).snapshot('TextEdit')
