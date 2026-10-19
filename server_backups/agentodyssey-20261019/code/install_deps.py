import subprocess,os
os.environ['DEBIAN_FRONTEND']='noninteractive'
subprocess.run(['apt-get','update','-qq'],check=True)
subprocess.run(['apt-get','install','-y','python3.10-venv'],check=True)
from bootstrap_remote import dependencies
dependencies()
