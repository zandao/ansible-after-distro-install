DIR := $(strip $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST)))))
GDRIVE := $(DIR)/gdrive-package.py
HOME := ${HOME}
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))

SUFFIXES: .files-gpkg-done .gpkg-done .enc-gpkg-done

%.files-gpkg-done::
	cd $(DIR)/files; $(GDRIVE) create $(basename $@ .files-gpkg-done) $(basename $<)
	@cd $(DIR); touch $@

%.gpkg-done::
	cd $(HOME); $(GDRIVE) create $(basename $@ .gpkg_done) $^
	@cd $(DIR); touch $@

%.enc-gpkg-done::
	@[ "${KEY}" ] && echo "Starting..." || ( echo "Use make backup KEY=<encryption key>"; exit 1 )
	@cd $(HOME); $(GDRIVE) --encryption-key "$(KEY)" create $(basename $@ .enc-gpkg-done) $^
	@cd $(DIR); touch $@

generate-installer-from-template: $(DIR)/scripts/install-pop-os.template
	argbash -o $(DIR)/install-pop-os $(DIR)/scripts/install-pop-os.template
	cp $(DIR)/install-pop-os $(HOME)

BACKUP_DEPS := fonts.files-gpkg-done vscode.gpkg-done documents.gpkg-done \
	shell.gpkg-done shell-encoded.enc-gpkg-done telegram-encoded.enc-gpkg-done \
	home-encoded.enc-gpkg-done home-config.gpkg-done gdrive.uploaded-gpkg-done \
	security.enc-gpkg-done deb.files-gpkg-done
FONTS_DEPS := $(DIR)/files/fonts
DEB_DEPS := $(DIR)/files/deb
VSCODE_DEPS := $(HOME)/.config/vscode-sqltools $(HOME)/.config/Code/User/settings.json
DOCUMENTS_DEPS := $(HOME)/Documents
SHELL_DEPS := $(HOME)/.oh-my-zsh $(HOME)/.profile $(HOME)/.p10k.zsh
SHELL_ENCODED_DEPS := $(HOME)/.zshrc $(HOME)/.zsh_history $(HOME)/.bash_history
TELEGRAM_ENCODED_DEPS := $(HOME)/.local/share/TelegramDesktop
HOME_ENCODED_DEPS := $(HOME)/.ssh $(HOME)/.pki $(HOME)/.rfb $(HOME)/.snxrc $(HOME)/.gnupg \
	$(HOME)/.config/remmina $(HOME)/.config/Insync $(HOME)/.local/share/Insync \
	$(HOME)/.config/exercism $(HOME)/.geekbench5 $(HOME)/.serpro
HOME_CONFIG_DEPS := $(HOME)/.ansible $(HOME)/.ansible.cfg $(HOME)/.config/alacritty \
	$(HOME)/.config/appimagelauncher.cfg $(HOME)/.config/autostart \
	$(HOME)/.config/blindspot $(HOME)/.config/calibre $(HOME)/.config/exercism \
	$(HOME)/.config/gnome-gmail $(HOME)/.config/kdeconnect $(HOME)/.config/kdeglobals \
	$(HOME)/.config/mimeapps.list $(HOME)/.config/pop-shell $(HOME)/.config/yamllint \
	$(HOME)/.gitconfig $(HOME)/.gwakeonlan $(HOME)/.tldr $(HOME)/.tool-versions \
	$(HOME)/.vimrc $(HOME)/.vim
SECURITY_ENCODED_DEPS := $(DIR)/files/x509 $(DIR)/files/security

backup: $(BACKUP_DEPS)

backup-fonts: fonts.filejs-gpkg-done
fonts.files-gpkg-done: $(FONTS_DEPS)

backup-deb: deb.files-gpkg-done
deb.files-gpkg-done: $(DEB_DEPS)

backup-vscode: vscode.gpkg-done
vscode.gpkg-done: $(VSCODE_DEPS)

backup-documents: documents.gpkg-done
documents.gpkg-done: $(DOCUMENTS_DEPS)

backup-shell: shell.gpkg-done
shell.gpkg-done: $(SHELL_DEPS)

backup-shell-enc: shell-encoded.enc-gpkg-done
shell-encoded.enc-gpkg-done: $(SHELL_ENCODED_DEPS)

backup-telegram-enc: telegram-encoded.enc-gpkg-done
telegram-encoded.enc-gpkg-done: $(TELEGRAM_ENCODED_DEPS)

backup-home-enc: home-encoded.enc-gpkg-done
home-encoded.enc-gpkg-done: $(HOME_ENCODED_DEPS)

backup-home: home-config.gpkg-done
home-config.gpkg-done: $(HOME_CONFIG_DEPS)

backup-security: security.enc-gpkg-done
security.enc-gpkg-done: $(SECURITY_ENCODED_DEPS)

upload-files: gdrive.uploaded-gpkg-done
gdrive.uploaded-gpkg-done: $(DIR)/install-pop-os
	cd $(DIR); $(GDRIVE) upload-file install-pop-os
	cd $(DIR); touch gdrive.uploaded-gpkg-done

.PHONY: clean list
clean:
	rm -f $(DIR)/install-pop-os $(HOME)/install-pop-os $(DIR)/*-gpkg-done
list:
	@awk -F ':' '!/^SUFFIXES:/ && /^[a-zA-Z_-]+:/ {print $$1}' $(mkfile_path) | sort
