---
REMOVE MY E-MAIL AND NAME FROM workstation-pop-os.yml

TASK [ensures single .deb packages are downloaded and installed] too slow when previously executed and packages already installed
TASK [add AppImages] too slow when previously executed and packages already installed

Install Vundle: git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim
    https://github.com/VundleVim/Vundle.vim#quick-start
    install bundles for java, javascript, typescript, node, etc.

Linix Mint Webapp Manager installation
  sudo gdebi http://packages.linuxmint.com/pool/main/l/linuxmint-keyring/linuxmint-keyring_2016.05.26_all.deb
  sudo sh -c 'echo "deb http://packages.linuxmint.com ulyssa main" >> /etc/apt/sources.list.d/mint.list'
  sudo gedit /etc/apt/preferences.d/mint-ulyssa-pin
      # Allow upgrading only webapp-manager from Ulyssa repository
      Package: webapp-manager
      Pin: release n=ulyssa
      Pin-Priority: 500
      
      # Never prefer other packages from the Ulyssa repository
      Package: *
      Pin: release n=ulyssa
      Pin-Priority: 1
  sudo apt update
  echo "Before installing the webapp-manager package, try command:"
  sudo apt install webapp-manager --simulate
  sudo apt install webapp-manager

Copy ./local/bin/get-monitors and .local/bin/monitors-order
./config/autostart/monitors-order.desktop

# External storage backup and restore

Migrate external storage from google drive to dropbox. Reason: https://www.goodcloudstorage.net/cloud-research/4-fastest-cloud-storage/

DON'T! - nameservers 1.1.1.1 then 8.8.8.8 then ubuntu default 
DON'T!   - /etc/default/docker:DOCKER_OPTS="--dns 8.8.8.8 --dns 8.8.4.4"
DON'T!   - /etc/resolvconf/resolv.conf.d/head:nameserver 8.8.8.8
- add multiple -creator calls to exiftool for multiple authors
- put https://spdx.org/licenses/GPL-2.0-only.html header on scripts
- check every path and file dependency that is not part of the repository before using it
- ansible_form_factor: Desktop. What other form-factors exist?
- add args: creates=<filename> to all shell commands
- put all deb packages lists inside a dictionary in packages.yml
- transfer more package installations from installer to worstation-install.yml
- install and configure zram only if ansible_memtotal_mb > 6000
- check supported architectures (ansible_architecture = x86_64)
- support more architectures (arm?)
- ansible_interfaces list enp* ou wlp* -> what configurations may be done to make network connections faster?
- make default shell configurable from command line or config file (today it just supports ansible_user_shell = /usr/bin/zsh)
- check if virtualization_role (guest or host) interfere in any task. Do we have any configuration that can't be done in virtualization environment (virtualization_role = guest)?
- supported environment limitations:
  - ansible_service_mgr: systemd
  - ansible_pkg_mgr: apt
  - ansible_lsb.id == 'Pop' && ansible_lsb.release == '21.04'
- instead of sourcing asdf inside every shell that uses asdf installed tool, declar as environment to playbook:
  environment:
    ASDF_DIR: "{{ user_dir }}/.asdf"
    PATH: {{ user_dir }}/.asdf/shims:{{ user_dir }}/.asdf/bin:{{ user_dir }}/.asdf/bin/asdf:{{ ansible_env.PATH }}"
