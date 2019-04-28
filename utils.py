import os, sys
import time
import subprocess, psutil

import requests, shutil
import json

USER_BASE='/content'

def status():
  print("\nDoing fine\n")
  return 

  
def gdrive_mount(point='gdrive', link='my_drive'):
  from google.colab import drive
  drive.mount(point)
  if link is not None:
    # ! ln -s "gdrive/My Drive" my_drive 
    # subprocess.run(["ln", "-s", point+"/My Drive", link,])
    subprocess.call(["ln", "-s", point+"/My Drive", link,])
    print("'%s' mounted as '%s'" % (point+"/My Drive", link,))


def download(url, base_path='.', unwrap=True, dest_path=None):
  if not os.path.exists(base_path):
    os.makedirs(base_path)

  # What type of file are we expecting
  url_path = requests.utils.urlparse( url ).path
  url_file = os.path.basename(url_path)
  urlfilepath = os.path.join(base_path, url_file)
  url_file_l = url_file.lower()
  
  is_zip, is_tar, is_tgz = url_file_l.endswith('.zip'), False, False
  if url_file_l.endswith('.tar'): 
    is_tar=True
  if url_file_l.endswith('.tar.gz') or url_file_l.endswith('.tgz'):
    is_tar, is_tgz=True, True

  fetch_url=True
  if os.path.isfile(urlfilepath):
    fetch_url=False  # No need to fetch
  
  dest_path_full=base_path  # default - but can't check for unwrapping
  if dest_path is not None:
    dest_path_full = os.path.join(base_path, dest_path) 
    
    if is_zip or is_tar: # Unwrappable
      # Does the dest_path have stuff in it?
      if os.path.isdir( dest_path_full ) and len(os.listdir( dest_path_full ))>0:
        print("'%s' already has files in it" % (dest_path_full,))
        return
        
  if not fetch_url:
    print("'%s' already present" % (urlfilepath,))
    pass
    
  else:
    # Download the missing file
    #urllib.request.urlretrieve(url, urlfilepath)
    response = requests.get(url, stream=True)
    if response.status_code == requests.codes.ok:
      print("Downloading %s" % (url,))
      with open(urlfilepath, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    else:
      print("FAILED TO DOWNLOAD %s" % (url,))
      return
  
  if unwrap and (is_zip or is_tar):
    if is_zip:
      print("Uncompressing .zip : '%s'" % (urlfilepath,))
      import zipfile
      zipfile.ZipFile(urlfilepath, 'r').extractall(dest_path_full)
    
    if is_tar:
      if is_tgz: 
        tar_flags='r:gz'
        print("Uncompressing .tar.gz : '%s'" % (urlfilepath,))
      else:
        tar_flags='r:'
        print("Unwrapping .tar : '%s'" % (urlfilepath,))
      import tarfile
      tarfile.open(urlfilepath, tar_flags).extractall(dest_path_full)
      #shutil.move(os.path.join(models_dir, models_orig_dir), os.path.join(models_dir, models_here_dir))

    if dest_path is not None and len(os.listdir( dest_path_full ))>0:
      # Something appeared in dest_path : no need for unwrapped file
      print("Deleting '%s'" % (urlfilepath,))
      os.unlink(urlfilepath)

  if len(os.listdir( dest_path_full ))>0:
    print("'%s' now contains data" % (dest_path_full,))  
    pass

"""
if not os.path.isfile( os.path.join(tf_zoo_models_dir, 'models', 'README.md') ):
    print("Cloning tensorflow model zoo under %s" % (tf_zoo_models_dir, ))
    !cd {tf_zoo_models_dir}; git clone https://github.com/tensorflow/models.git

sys.path.append(tf_zoo_models_dir + "/models/research/slim")
"""

def kaggle_credentials(username=None, key=None, file=None):
  """
  Put the kaggle credentials in the right place, 
  with the right permissions.  You can generate the 
  kaggle.json file from the 'My Account' page 
  in the 'API' section using the 'Create New API Token' button, or 
  just use your username with the generated key
  """
  kaggle_path = '/root'+'/.kaggle'  # Must be in /root/ not /content/
  kaggle_file = kaggle_path+'/kaggle.json'
  
  if username is None or key is None:
    if file is None:
      print("Please specify username+key (from Kaggle-My Account page, or file")
      return
    else:
      # use the file provided
      with open(file,'rt') as f:
        data = json.load(f)
        username, key = data['username'], data['key']
        
  data = dict( username=username, key=key )
  
  if not os.path.exists(kaggle_path):
    os.makedirs(kaggle_path)
    
  with open(kaggle_file, 'w') as f:
    json.dump(data, f)
  os.chmod(kaggle_file, 0o600)
  
  print("Credentials written to %s" % (kaggle_file,))



# https://colab.research.google.com/notebooks/io.ipynb#scrollTo=S7c8WYyQdh5i
# Fuse mounting approach :
#   https://cloud.google.com/storage/docs/gcs-fuse
#   https://github.com/GoogleCloudPlatform/gcsfuse/blob/master/docs/installing.md
# More helpful than Google installation instructions...
#   https://github.com/mixuala/colab_utils/blob/master/gcloud.py#L599
def gcs_mount():
  pass
  


def _RunningProcessCmdlines(processName):
  '''
  Check if there is any running process that contains the given name processName.
  '''
  cmds=[]
  for proc in psutil.process_iter():
    try:
      # Check if process name contains the given name string.
      if processName.lower() in proc.name().lower():
        cmds.append( proc.cmdline() )
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
      pass
  return cmds
      
def ssh_reverse_proxy(pub_key, host='serveo.net', port=22, jump=True):
  import socket, os
  subdomain = 'colab_' + socket.gethostname()

  sshd = '/usr/sbin/sshd'
  if len(_RunningProcessCmdlines(sshd))==0:
    if not os.path.isdir("/var/run/sshd"):
      os.mkdir("/var/run/sshd", mode=0o755)
    # get_ipython().system_raw('/usr/sbin/sshd -D &')
    proc = subprocess.Popen([sshd, '-D', '&'], shell=True)
    print("sshd pid = %d" % (proc.pid,))

  while len(_RunningProcessCmdlines('/usr/sbin/sshd'))==0:
    print("Wait on sshd start")
    time.sleep(0.1)
    
  if not os.path.isdir("/root/.ssh"):
    os.mkdir("/root/.ssh", mode=0o700)

  key_exists=False
  if os.path.isfile("/root/.ssh/authorized_keys"):
    with open('/root/.ssh/authorized_keys', 'rt') as ak:
      for l in ak:
        if pub_key in l:
          key_exists=True
          
  if not key_exists:
    with open('/root/.ssh/authorized_keys', 'at') as ak:
      ak.write(pub_key)
      ak.write("\n")
    os.chmod('/root/.ssh/authorized_keys', 0o600)
  
  ssh = '/usr/bin/ssh'
  ssh_cmds = [ ' '.join(c) for c in _RunningProcessCmdlines(ssh) ]
  print("ssh_cmds :", ssh_cmds)
  has_22 = [ True for s in ssh_cmds if '22:localhost:22' in s ]
  print("has_22 :", has_22)
  
  if len(has_22)==0:
    # get_ipython().system_raw('ssh -o StrictHostKeyChecking=no -R %s:22:localhost:22 serveo.net &' % (subdomain,))  # Has entry in `ps fax`
    # get_ipython().system_raw('ssh -o StrictHostKeyChecking=no -R %s:22:localhost:22 serveo.net &' % ('colab_ea8f2354f97c',))  # Has entry in `ps fax`
    proc = subprocess.Popen([ssh, '-o', 'StrictHostKeyChecking=no', 
                                    '-R', '%s:22:localhost:22' % (subdomain,), 
                                    '%s' % (host,), 
                                    '&'], shell=True)
    print(' '.join([ssh, '-o', 'StrictHostKeyChecking=no', 
                                    '-R', '%s:22:localhost:22' % (subdomain,), 
                                    '%s' % (host,), 
                                    '&']))
    print("ssh proxy pid = %d" % (proc.pid,))

  if jump:
    print("\n# Your public key is in authorized_keys, so no password required - Execute locally:")
    print("ssh -J %s root@%s" % (host, subdomain,))
  else:
    print("Non-jump hosts not supported, yet")



# Show logo on load...

import matplotlib.pyplot as plt
from PIL import Image
import numpy as np

img_path = os.path.join( os.path.dirname(os.path.abspath(__file__)), 'img', 'RedDragon_logo_260x39.png')
pil_im = Image.open(img_path) 
plt.imshow(np.asarray(pil_im))
plt.axis('off')
plt.show()
