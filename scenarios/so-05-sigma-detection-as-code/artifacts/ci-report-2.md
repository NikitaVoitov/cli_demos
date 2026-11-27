## Detection tests

| Detection | Case | Expected | ESCU rule | This detection | Result |
|---|---|---|---|---|---|
| HackTool Mimikatz Execution | attack_data T1003.001: mimikatz sekurlsa::minidump | fires | - | fires | pass |
| HackTool Mimikatz Execution | crafted: cmd.exe whoami /all | silent | - | silent | pass |
| HackTool Mimikatz Execution | crafted: nightly purple-team run on PT-LAB-01 (excluded, CHG-2077) | silent | - | silent | pass |
| Potential LSASS Process Dump Via Procdump | attack_data T1003.001: procdump -ma lsass.exe | fires | fires | fires | pass |
| Potential LSASS Process Dump Via Procdump | crafted: procdump of a hung IIS worker (w3wp.exe) | silent | silent | silent | pass |
| Potential LSASS Process Dump Via Procdump | crafted: nightly purple-team run on PT-LAB-01 (excluded, CHG-2077) | silent | fires | silent | pass |
| Process Memory Dump Via Comsvcs DLL | attack_data T1003.001: rundll32 comsvcs.dll MiniDump lsass | fires | fires | fires | pass |
| Process Memory Dump Via Comsvcs DLL | crafted: ordinal #+24 (ESCU needs #24 or MiniDump) | fires | silent | fires | pass |
| Process Memory Dump Via Comsvcs DLL | crafted: wrapped ordinal #65560 = 24 (ESCU misses) | fires | silent | fires | pass |
| Process Memory Dump Via Comsvcs DLL | crafted: negative ordinal #-65512 (ESCU misses) | fires | silent | fires | pass |
| Process Memory Dump Via Comsvcs DLL | crafted: rundll32 loads comsvcs.dll RegisterComponent, no dump | silent | silent | silent | pass |
| Process Memory Dump Via Comsvcs DLL | crafted: nightly purple-team run on PT-LAB-01 (excluded, CHG-2077) | silent | fires | silent | pass |

## Noise: last 7 days of `demo_endpoint` (budget 5 alerts)

| Detection | Alerts | Result |
|---|---|---|
| HackTool Mimikatz Execution | 0 | pass |
| Potential LSASS Process Dump Via Procdump | 0 | pass |
| Process Memory Dump Via Comsvcs DLL | 0 | pass |

**PASSED**: 12/12 cases pass; 0 detection(s) over the noise budget.
