#!/usr/bin/env python

from fireworks import LaunchPad

if __name__ = '__main__':
    launchpad = LaunchPad(host='localhost', port=27017, name='fireworks',
                          username="km468", password="km468")
#reset launchpad
# Create a new FireWorks database. This will overwrite the existing FireWorks database!
#To safeguard against accidentally erasing an existing database, a password must
#be entered.
#
    print launchpad.get_fw_ids()

    launchpad.reset('', require_password=False)

    print launchpad.get_fw_ids()