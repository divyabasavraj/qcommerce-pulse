import json, sys
from qpulse import dashboard_data

json.dump(dashboard_data.weekly(), sys.stdout)
