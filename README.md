# pstow
A spiritual reimplementation of GNU Stow, for tinkerers.

A fancy way to softlink your dotfiles to their intended destination.

## Intent
This started as a [personal](https://github.com/gerelef/) side project in order to facilitate the easy one-line 
deployment of my entire dotfile structure.

A critical feature (`redirect`s) was added as a personal requirement. 
I decided to open-source this utility in sight of the fact that people might require the same solution I did.
Keep in mind there are valid alternatives to this utility; keep your options open.
### Features
- `.stowconfig`
- Lightweight.
- Clear-cut & simple to use.
- Ignorables, meaning files & directories that will be excluded.
- Redirectables, meaning files that will be redirected (moved) to a virtual directory of your own choosing. \
You can see this in use in [my dotfiles](https://github.com/gerelef/dotfiles).
- Dynamic targets (supported through redirects.)
- Multiple targets (supported through redirects.)
You may opt to avoid conforming to a 1:1 relationship between your dotfiles' directory structure & their target, 
unlike a `bare` git repo, which is often the most common "recipe".  

## Usage
This is the help text:
```
usage: A spiritual reimplementation, of GNU Stow. [--help] 
                                                  [--source SOURCE]
                                                  [--target TARGET]
                                                  [--enforce-integrity]
                                                  [--force] [--yes]
                                                  [--overwrite-others]
                                                  [--exclude EXCLUDE [EXCLUDE ...]]
                                                  [--no-parents]
                                                  [--no-redirects]
                                                  {status}

positional arguments:
  status                     Echo the current status of the stow src and exit.

options:
  -h, --help                 Show this help message and exit.
  
  --source SOURCE, -s SOURCE Source directory links will be linked from.
  
  --target TARGET, -t TARGET Target (destination) directory links will be linked to.
  
  --enforce-integrity, -i    Enforce integrity of any .stowconfig encountered;
                             a.k.a. stop at any error.     
                                                
  --force, -f                Force overwrite of any conflicting file. This WILL
                             overwrite regular files!
                             
  --yes, -y                  Automatically assume 'yes' for any user prompt.
                             Dangerous flag, possibly destructive!
                             
  --overwrite-others, -o     Overwrite links/files owned by other users than the
                             current one.Default behaviour is to not overwrite
                             files not owned by the current user.Functionally the
                             same as --no-preserve-root in the rm command.
  --exclude EXCLUDE [EXCLUDE ...], -e EXCLUDE [EXCLUDE ...]
                             Exclude (ignore) a specific directory when copying the
                             tree. Multiple values can be given.Symlinks are not
                             supported as exclusion criteria.
                             
  --no-parents, -p           Don't make parent directories as we traverse the tree
                             in destination, even if they do not exist.
                             
  --no-redirects, -r         Don't respect redirects in any encountered stowconfig.
```
Here's an example usage of this utility:
```bash
pstow.py --source ~/dotfiles --target ~ status
```
This will output the final target structure, and stop before committing any possibly destructive action. 

Example (non-coloured) output, from [my own dotfiles](https://github.com/gerelef/dotfiles):
```bash
 ~/dotfiles (main)> pstow status
 dotfiles/
───> .bashrc
───> .gitconfig
───> .nanorc
───> .config/
───────> alacritty/
───────────> alacritty.toml
───────> fish/
───────────> config.fish
───────────> functions/
───────────────> fish_prompt.fish
───────> lsd/
───────────> config.yaml
───────> pipewire/
───────────> pipewire.conf
───────> sublime-text/
───────────> Packages/
───────────────> User/
───────────────────> Default (Linux).sublime-keymap
───────────────────> Default (Linux).sublime-mousemap
───────────────────> Package Control.sublime-settings
───────────────────> Preferences.sublime-settings
───> .mozilla/
───────> firefox/
───────────> 7hc3epgjk.default/
───────────────> user.js
───────────> jac1gzgck.default-release/
───────────────> user.js
───> Templates/
───────> Bash.sh
───────> LibreOffice Calc Sheet.ods
───────> LibreOffice Impress Slides.odp
───────> LibreOffice Writer Document.odt
───────> Markdown.md
───────> Python.py
───────> Text Document.txt
WARNING: Aborting.
```
In the example above, a semi-standard `XDG` directory layout is emulated, from `~/dotfiles`, w/ the target being `~`.
The following files & directories are `virtual`,  e.g. they do not exist in the dotfiles structure, yet they act like they do:
- `.bashrc`, `.nanorc`, `.gitconfig` are virtual; they exist in `scripts/*`, however they're a level up, because they were redirected.
- `.config/fish/functions/fish_prompt.fish` & it's parent directory are virtual; only the file actually exists, and it's in the `fish/` directory.
- `.config/lsd/config.yaml`, `.config/pipewire/pipewire.conf`, `.config/alacritty/alacritty.toml` are virtual; they're all actually exist in the `.config/` directory.
- The nested `.config/sublime-text/Packages/User/*` files are all virtual; they actually belong in `.config/sublime-text`.
- `.mozilla/firefox/*.default*/` directories are 100% virtual; they only exist in context of the target, and \
`user.js` is a redirected dynamic multi-target file originally from `.config/mozilla/user.js`. \
Dynamic multi-target (globbable-redirected) files can only be resolved with the context of a valid target; \
if the non-emulated directories, on the target, do not already exist, they will not be created.  
- `Templates/` is a redirected directory from `.config/templates/`.

This is all accomplished through the use of `.stowconfig`(s). \
Here's the one used for the output above, which'll hopefully will be well commented. \
Please also check out commit `6caa907` from [my personal dotfiles](https://github.com/gerelef/dotfiles) 
to accompany this config:
```stowconfig
 ~/dotfiles (main)> cat .stowconfig
// Ignore header is implied, since it's the first thing in the .stowconfig
.git*
README.*

// these are configuration files specifically for the dotfiles directory
// and as such, they shouldn't be redirected (stowed) anywhere else
.stowconfig
.shell-requirements

// ignore these since they're not meant to be linked anywhere
scripts/utils/
scripts/setup/
scripts/functions/
.manpages/
// ignore submodules
games/

// firefox-specific redirect ignores; these are not true config files
// and must be imported manually
.config/mozilla/sidebery.json
.config/mozilla/ublock.txt
.config/mozilla/userChrome.css

// these are not true config files, they must be imported manually
.config/gnome-extensions/

[redirect]
// redirect to home (move up)
scripts/.bashrc ::: .
scripts/.nanorc ::: .
scripts/.gitconfig ::: .

// move up & rename directory
.config/templates/* ::: Templates/

// redirect to nested (not created necessarily) directory
.config/alacritty.toml ::: .config/alacritty/
.config/pipewire.conf ::: .config/pipewire/
.config/config.yaml ::: .config/lsd/

// create subdirectories on the fly, don't nest unecessarily
.config/sublime-text/* ::: .config/sublime-text/Packages/User/
.config/fish/fish_prompt.fish ::: .config/fish/functions/

// find already created profile subdirectories on the fly
.config/mozilla/* ::: .mozilla/firefox/*.default*/
```
The first section is always the `[ignore]` section, as implied by the lack of header. 

The second section `[redirect]` is inferred from the header. 

Comments are allowed after a newline; they cannot be inlined. \
They were not added as mocks/explanations for this section; they are there in the original configuration file.

Syntax for `redirect` entries must match the following regex to be valid: `\"?(.+)\"?\s+(:::)\s+\"?(.+)\"?` \
The destination **must** be a directory. This is a hard limitation currently & is non-negotiable. 

See _Limitations_ section below.

### Limitations
Targets for `redirect` entries can only be directories; they cannot be files (which might or might not be renamed).
This is a technical limitation of the current implementation. \
Steps are being slowly taken to solve this, no promises though.

## Supported platforms
GNU/Linux only.
