#!/usr/bin/env python
# -*- coding: utf-8 -*-

def test_help_option(script_runner):
    ret = script_runner.run(["wm_quality_control_tractography.py", "--help"])
    assert ret.success
