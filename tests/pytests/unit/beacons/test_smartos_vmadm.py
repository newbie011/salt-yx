# Python libs
import pytest

# Salt libs
import salt.beacons.smartos_vmadm as vmadm
from tests.support.mock import MagicMock, patch


@pytest.fixture
def configure_loader_modules():
    return {vmadm: {"__context__": {}, "__salt__": {}}}


@pytest.fixture
def mock_clean_state():
    return {"first_run": True, "vms": []}


@pytest.fixture
def mock_vm_none():
    return {}


@pytest.fixture
def mock_vm_one():
    return {
        "00000000-0000-0000-0000-000000000001": {
            "state": "running",
            "alias": "vm1",
            "hostname": "vm1",
            "dns_domain": "example.org",
        },
    }


@pytest.fixture
def mock_vm_two_stopped():
    return {
        "00000000-0000-0000-0000-000000000001": {
            "state": "running",
            "alias": "vm1",
            "hostname": "vm1",
            "dns_domain": "example.org",
        },
        "00000000-0000-0000-0000-000000000002": {
            "state": "stopped",
            "alias": "vm2",
            "hostname": "vm2",
            "dns_domain": "example.org",
        },
    }


@pytest.fixture
def mock_vm_two_started():
    return {
        "00000000-0000-0000-0000-000000000001": {
            "state": "running",
            "alias": "vm1",
            "hostname": "vm1",
            "dns_domain": "example.org",
        },
        "00000000-0000-0000-0000-000000000002": {
            "state": "running",
            "alias": "vm2",
            "hostname": "vm2",
            "dns_domain": "example.org",
        },
    }


def test_non_list_config():
    """
    We only have minimal validation so we test that here
    """
    config = {}

    ret = vmadm.validate(config)

    assert ret == (False, "Configuration for vmadm beacon must be a list!")


def test_created_startup(mock_clean_state, mock_vm_one):
    """
    Test with one vm and startup_create_event
    """
    # NOTE: this should yield 1 created event + one state event
    with patch.dict(vmadm.VMADM_STATE, mock_clean_state), patch.dict(
        vmadm.__salt__, {"vmadm.list": MagicMock(return_value=mock_vm_one)}
    ):

        config = [{"startup_create_event": True}]

        ret = vmadm.validate(config)
        assert ret == (True, "Valid beacon configuration")

        ret = vmadm.beacon(config)
        res = [
            {
                "alias": "vm1",
                "tag": "created/00000000-0000-0000-0000-000000000001",
                "hostname": "vm1",
                "dns_domain": "example.org",
            },
            {
                "alias": "vm1",
                "tag": "running/00000000-0000-0000-0000-000000000001",
                "hostname": "vm1",
                "dns_domain": "example.org",
            },
        ]
        assert ret == res


def test_created_nostartup(mock_clean_state, mock_vm_one):
    """
    Test with one image and startup_import_event unset/false
    """
    # NOTE: this should yield 0 created event _ one state event
    with patch.dict(vmadm.VMADM_STATE, mock_clean_state), patch.dict(
        vmadm.__salt__, {"vmadm.list": MagicMock(return_value=mock_vm_one)}
    ):

        config = []

        ret = vmadm.validate(config)
        assert ret == (True, "Valid beacon configuration")

        ret = vmadm.beacon(config)
        res = [
            {
                "alias": "vm1",
                "tag": "running/00000000-0000-0000-0000-000000000001",
                "hostname": "vm1",
                "dns_domain": "example.org",
            }
        ]

        assert ret == res


def test_created(mock_clean_state, mock_vm_one, mock_vm_two_started):
    """
    Test with one vm, create a 2nd one
    """
    # NOTE: this should yield 1 created event + state event
    with patch.dict(vmadm.VMADM_STATE, mock_clean_state), patch.dict(
        vmadm.__salt__,
        {"vmadm.list": MagicMock(side_effect=[mock_vm_one, mock_vm_two_started])},
    ):

        config = []

        ret = vmadm.validate(config)
        assert ret == (True, "Valid beacon configuration")

        # Initial pass (Initialized state and do not yield created events at startup)
        ret = vmadm.beacon(config)

        # Second pass (After create a new vm)
        ret = vmadm.beacon(config)
        res = [
            {
                "alias": "vm2",
                "tag": "created/00000000-0000-0000-0000-000000000002",
                "hostname": "vm2",
                "dns_domain": "example.org",
            },
            {
                "alias": "vm2",
                "tag": "running/00000000-0000-0000-0000-000000000002",
                "hostname": "vm2",
                "dns_domain": "example.org",
            },
        ]

        assert ret == res


def test_deleted(mock_clean_state, mock_vm_two_stopped, mock_vm_one):
    """
    Test with two vms and one gets destroyed
    """
    # NOTE: this should yield 1 destroyed event
    with patch.dict(vmadm.VMADM_STATE, mock_clean_state), patch.dict(
        vmadm.__salt__,
        {"vmadm.list": MagicMock(side_effect=[mock_vm_two_stopped, mock_vm_one])},
    ):

        config = []

        ret = vmadm.validate(config)
        assert ret == (True, "Valid beacon configuration")

        # Initial pass (Initialized state and do not yield created vms at startup)
        ret = vmadm.beacon(config)

        # Second pass (Destroying one vm)
        ret = vmadm.beacon(config)
        res = [
            {
                "alias": "vm2",
                "tag": "deleted/00000000-0000-0000-0000-000000000002",
                "hostname": "vm2",
                "dns_domain": "example.org",
            }
        ]

        assert ret == res


def test_complex(
    mock_clean_state, mock_vm_one, mock_vm_two_started, mock_vm_two_stopped
):
    """
    Test with two vms, stop one, delete one
    """
    # NOTE: this should yield 1 delete and 2 import events
    with patch.dict(vmadm.VMADM_STATE, mock_clean_state), patch.dict(
        vmadm.__salt__,
        {
            "vmadm.list": MagicMock(
                side_effect=[mock_vm_two_started, mock_vm_two_stopped, mock_vm_one]
            )
        },
    ):

        config = []

        ret = vmadm.validate(config)
        assert ret == (True, "Valid beacon configuration")

        # Initial pass (Initialized state and do not yield created events at startup)
        ret = vmadm.beacon(config)

        # Second pass (Stop one vm)
        ret = vmadm.beacon(config)
        res = [
            {
                "alias": "vm2",
                "tag": "stopped/00000000-0000-0000-0000-000000000002",
                "hostname": "vm2",
                "dns_domain": "example.org",
            }
        ]

        assert ret == res

        # Third pass (Delete one vm)
        ret = vmadm.beacon(config)
        res = [
            {
                "alias": "vm2",
                "tag": "deleted/00000000-0000-0000-0000-000000000002",
                "hostname": "vm2",
                "dns_domain": "example.org",
            }
        ]

        assert ret == res
