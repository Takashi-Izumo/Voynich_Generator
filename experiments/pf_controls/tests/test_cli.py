import io
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from experiments.pf_controls.__main__ import main
from experiments.pf_controls import pipeline


class CLIContractTests(unittest.TestCase):
    def test_verify_export_accepts_the_documented_cli_and_calls_api(self):
        argv=['pf_controls','verify-export','--plan','plan.json','--generated','generated','--exported','exported']
        with patch.object(sys,'argv',argv),patch.object(pipeline,'verify_export',autospec=True) as verify,redirect_stdout(io.StringIO()) as output:
            main()
        verify.assert_called_once_with('plan.json','generated','exported')
        self.assertIn('COMPLETE',output.getvalue())

    def test_verify_export_requires_exported_argument_before_calling_api(self):
        with patch.object(sys,'argv',['pf_controls','verify-export','--plan','p','--generated','g']),\
             patch.object(pipeline,'verify_export',autospec=True) as verify,\
             patch('sys.stderr',io.StringIO()):
            with self.assertRaises(SystemExit):main()
        verify.assert_not_called()
