---
# Post-install

URGENT: export ANSIBLE_CALLBACK_PLUGINS="$(python3 -m ara.setup.callback_plugins)"
put it on .zshrc

## Software to test

- https://starship.rs/
- https://www.nerdfonts.com/

## Configuration (not yet in ansible playbook)

- IF INTEL GPU, INSTALL:
  - i965-va-driver/hirsute 2.4.1+dfsg1-1 amd64
    VAAPI driver for Intel G45 & HD Graphics family
  - i965-va-driver-shaders/hirsute,now 2.4.1-1 amd64 [installed]
    VAAPI driver for Intel G45 & HD Graphics family
  - vainfo
  - xserver-xorg-video-intel/hirsute,now 2:2.99.917+git20200714-1ubuntu1 amd64 [installed,automatic]
    X.Org X server -- Intel i8xx, i9xx display driver
- Configures VirtualBox extension pack
- Disable swap in fstab or during linux installation
- Configuration of backup software
  - https://github.com/teejee2008/timeshift
- Install ventoy (https://github.com/ventoy/Ventoy/releases/download/v1.0.46/ventoy-1.0.46-linux.tar.gz)
- Open Libre Office Writer → Tools → Options → Libre Office → Advanced
  - Java options: Remove "Use a Java runtime environment" checkbox
- Install with blindspot:
  - BurntSushi/ripgrep       https://github.com/BurntSushi/ripgrep
  - chmln/sd                 https://github.com/chmln/sd
  - dalance/procs --completion zsh  https://github.com/dalance/procs
  - dbrgn/tealdeer           https://github.com/dbrgn/tealdeer https://github.com/dbrgn/tealdeer/releases/download/v1.4.1/completions_zsh
  - hlmtre/homemaker         https://github.com/hlmtre/homemaker
  - imsnif/bandwhich         https://github.com/imsnif/bandwhich
  - orhun/gpg-tui            https://github.com/orhun/gpg-tui
  - pemistahl/grex           https://github.com/pemistahl/grex
  - SirWindfield/git-cm      https://github.com/SirWindfield/git-cm
  - taiki-e/parse-changelog  https://github.com/taiki-e/parse-changelog
  - TheZoraiz/ascii-image-converter  https://github.com/TheZoraiz/ascii-image-converter
  - XAMPPRocky/tokei         https://github.com/XAMPPRocky/tokei
- Manual install
  - https://timewarrior.net/
  - http://todotxt.org/
- Reading
  - https://github.com/dandavison/delta
  - https://github.com/sharkdp/bat
  - https://github.com/MitMaro/git-interactive-rebase-tool
  - https://github.com/brocode/fw/
  - https://github.com/ClementTsang/bottom
  - https://github.com/bvaisvil/zenith
  - https://github.com/dawidm/cryptonose2
  - https://github.com/sharkdp/fd
  - https://github.com/BurntSushi/ripgrep
  - https://github.com/romkatv/powerlevel10k#oh-my-zsh
  - https://github.com/romkatv/powerlevel10k#meslo-nerd-font-patched-for-powerlevel10k
  - https://github.com/ryanoasis/powerline-extra-symbols
  - https://www.conventionalcommits.org/en/v1.0.0/
  - https://github.com/ImaginarySense/Imaginary-Teleprompter-Electron/
  - https://github.com/orhun/gpg-tui
  - https://github.com/pndurette/gTTS
  - https://github.com/deezer/spleeter
  - https://starship.rs/guide/#%F0%9F%9A%80-installation

## Pentaho TRT3 installation

- Install Pentaho dependencies:
  - "http://security.ubuntu.com/ubuntu/pool/main/i/icu/libicu60_60.2-3ubuntu3.1_amd64.deb"
  - "http://security.ubuntu.com/ubuntu/pool/main/w/webkitgtk/libjavascriptcoregtk-1.0-0_2.4.11-3ubuntu3_amd64.deb"
  - "http://security.ubuntu.com/ubuntu/pool/universe/w/webkitgtk/libwebkitgtk-1.0-0_2.4.11-3ubuntu3_amd64.deb"

## Limiting the disk write actions of Chrome

Already done if restoring chrome .config/chrome configuration.

The disk write actions of Google Chrome can be limited as follows: in Developer Tools, Networking, disable cache.

## Limiting the disk write actions of Firefox

Already done if restoring firefox .mozilla configuration.

You can limit the disk write actions of Firefox, by putting the Firefox network cache into the RAM and by disabling sessionstore. Like this:

   1. By moving the Firefox network cache from your hard disk to the RAM, you diminish the amount of disk writes. 
      1. Type in the URL bar of Firefox: about:config
      2. Search bar: browser.cache.disk.enable
         Toggle its value to false by double-clicking it: this will disable "cache to disk" entirely.
      3. Check if "cache to RAM" is enabled. Search bar: browser.cache.memory.enable
      4. Check how much memory can be used as RAM cache. Search bar: browser.cache.memory.capacity
         - Enter the integer value in KB; I advise 204800 (which equals 200 MB).
      5. Close Firefox and launch it again. You're done! Check it like this: about:cache
   2. Firefox has a session restore feature. Disable it like this:
      1. Type in the URL bar of Firefox: about:config
      2. Type in the filter bar: browser.sessionstore.interval
      3. The default interval is 15000, which means 15 seconds. Change it to 120000 (2 min.)
