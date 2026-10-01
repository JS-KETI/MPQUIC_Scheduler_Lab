import difflib
from pathlib import Path
import subprocess

root = Path('/home/ubuntu/projects/keti/mpquic-sched-lab/mpquic')
file = root / 'scratch/wns3-mpquic-one-path.cc'
original = file.read_text()
modified = original.replace('#include <iostream>', '#include <iostream>\n#include <iomanip>', 1)
marker = 'NS_LOG_COMPONENT_DEFINE("wns3-mpquic-one-path");'
assert modified.count(marker) == 1
callback = '''

// Week 1: passive application receive measurement; no simulation behavior changes.
static uint64_t g_w1Rx = 0;
static uint64_t g_w1Size = 0;
static double g_w1Fct = -1.0;
static double g_w1FctFull = -1.0;
static void Week1SinkRx (Ptr<const Packet> packet, const Address &from)
{
    g_w1Rx += packet->GetSize ();
    const double elapsed = Simulator::Now ().GetSeconds () - 1.0;
    if (g_w1Fct < 0 && g_w1Rx >= (g_w1Size > 3000 ? g_w1Size - 3000 : g_w1Size))
        g_w1Fct = elapsed;
    if (g_w1FctFull < 0 && g_w1Rx >= g_w1Size)
        g_w1FctFull = elapsed;
}
'''
modified = modified.replace(marker, marker + callback, 1)
marker = 'uint32_t maxBytes = stoi(myRandomNo);'
assert modified.count(marker) == 1
modified = modified.replace(marker, marker + '\n    g_w1Size = maxBytes;', 1)
marker = 'sinkApps2.Stop (Seconds(simulationEndTime));'
assert modified.count(marker) == 1
modified = modified.replace(marker, marker + '\n    sinkApps2.Get (0)->TraceConnectWithoutContext ("Rx", MakeCallback (&Week1SinkRx));', 1)
marker = '    Simulator::Destroy ();'
assert modified.count(marker) == 1
output = '''    std::cout << std::fixed << std::setprecision (9) << "RESULT_ONE_PATH,"
              << schedulerType << "," << seed << "," << maxBytes << ","
              << g_w1Fct << "," << g_w1FctFull << "," << g_w1Rx << std::endl;

'''
modified = modified.replace(marker, output + marker, 1)
patch = ''.join(difflib.unified_diff(original.splitlines(keepends=True), modified.splitlines(keepends=True), fromfile='a/scratch/wns3-mpquic-one-path.cc', tofile='b/scratch/wns3-mpquic-one-path.cc'))
patch_path = root.parent / 'patches/04-week1-one-path-measurement.patch'
assert not patch_path.exists()
patch_path.write_text(patch)
subprocess.run(['git', 'apply', '--check', str(patch_path)], cwd=root, check=True)
subprocess.run(['git', 'apply', str(patch_path)], cwd=root, check=True)
print('Applied passive single-path measurement patch:', patch_path)
