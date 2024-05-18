# pstow
A spiritual reimplementation of GNU Stow, for tinkerers.

A fancy way to softlink your dotfiles to their intended destination.

## Intent
This started as a [personal](https://github.com/gerelef/) side project in order to facilitate the easy one-line 
deployment of my entire dotfile structure.

A critical feature (`redirect`s) was added as a personal requirement. \
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
- Conditional cases, supported through the following blocks:
```stowconfig
// all packages MUST exist in non-interactive, non-login $SHELL
[if-pkg:::pkg1 pkg2 pkg3 ...]
...
[end]
// all packages MUST NOT exist in non-interactive, non-login $SHELL
[if-not-pkg:::pkg1 pkg2 pkg3 ...]
...
[end]
// current profile MUST exist in the profile list 
[if-profile:::profile1 profile2 ...]
...
[end]
// current profile MUST NOT exist in the profile list
[if-not-profile:::profile1 profile2 ...]
...
[end]
```
You may opt to avoid conforming to a 1:1 relationship between your dotfiles' directory structure & their target, 
unlike a `bare` git repo, which is often the most common "recipe".  

## Zero-to-hero for .stowconfig & interactive demo
### prerequisites
- python3.12

### demo
First, clone the repository:
```bash
git clone git@github.com:gerelef/pstow.git && cd ./pstow
```
We need a workspace to try out `pstow`. \
Create a mock playground by running `./generate-mock-dotfiles.py` while inside the `pstow` directory:
```bash
./generate-mock-dotfiles && cd ./dotfiles
```
Now you should be inside the `~/.../pstow/dotfiles` directory. Great! We're ready to get started. \
Let's start with a dry run; this will display what is ready to be symlinked to the target of your choosing. 
It won't affect your filesystem! \
We're going to be explicit here about our destination (`--target <path>`):
```bash
~/.../dotfiles (changes) $ ../pstow.py --target ~ status
# ... output too long to print here
```
*Nice.* \
When running `pstow` with the `status` subcommand, we're going to get a display of whatever would be linked, \
in relation to the root dotfiles directory.
We're getting alot of output, mostly from directories we definitely don't want to symlink. \
Lets change that! We're going to be verbose, manually excluding everything, once again from the shell:
```bash
 ~/.../dotfiles (changes) $ ../pstow.py --exclude .config/ .git/ scripts/ manpages/ --target ~ status
  dotfiles/
 dotfiles/
───> .gitconfig
───> .has-run
───> .shell-requirements
───> .stowconfig
───> baraction.sh
───> cju.conf
───> config.conf
───> dui.yml
───> macho-gui.sh
───> macho.sh
WARNING: Aborting.
```
The status output was whatever was in the root dotfiles directory. Great! This means we can explicitly, on-demand,
exclude whatever files we don't want to symlink manually. \
However, it'd be alot cooler if we could do this automatically rather than remembering random shell incantations... \
Let's start by creating a `.stowconfig` in the root dotfiles directory. \
If it exists, don't worry! Just overwrite the contents & paste the following:
```
*.md
.git/
manpages/
scripts/
.config/
```
Now let's run the first command we run originally:
```bash
 ~/.../dotfiles (changes) $ ../pstow.py --target ~ status
 dotfiles/
───> .gitconfig
───> .has-run
───> .shell-requirements
───> .stowconfig
───> baraction.sh
───> cju.conf
───> config.conf
───> dui.yml
───> macho-gui.sh
───> macho.sh
WARNING: Aborting.
```
Our output is the same as if we manually excluded the aforementioned directories. \
This means our `pstow` configuration works! \



## --help
```
usage: A spiritual reimplementation of GNU Stow, but simpler, for tinkerers. [-h] [--source SOURCE] [--target TARGET] [--enforce-integrity] [--force] [--yes] [--overwrite-others]
                                                                             [--exclude EXCLUDE [EXCLUDE ...]] [--profile PROFILE] [--no-parents] [--no-redirects]
                                                                             {status} ...

positional arguments:
  {status}
    status              Echo the current status of the stow source.

options:
  -h, --help            show this help message and exit
  --source SOURCE, -s SOURCE
                        Source directory links will be linked from.
  --target TARGET, -t TARGET
                        Target (destination) directory links will be linked to.
  --enforce-integrity, -i
                        Enforce integrity of any .stowconfig encountered; a.k.a. stop at any error.
  --force, -f           Force overwrite of any conflicting file. This WILL overwrite regular files!
  --yes, -y             Automatically assume 'yes' for any user prompt. Dangerous flag, possibly destructive!
  --overwrite-others, -o
                        Ovewrite links/files owned by other users than the current one. Default behaviour is to not overwrite files not owned by the current user. Functionally the same as
                        --no-preserve-root in the rm command.
  --exclude EXCLUDE [EXCLUDE ...], -e EXCLUDE [EXCLUDE ...]
                        Exclude (ignore) a specific directory when copying the tree. Multiple values can be given. Symlinks are not supported as exclusion criteria.
  --profile PROFILE, -p PROFILE
                        Profile to use when loading .stowconfigs.This will affect all if-profile and if-not-profile blocks accordingly.
  --no-parents, -n      Don't make parent directories as we traverse the tree in destination, even if they do not exist.
  --no-redirects, -r    Don't respect redirects in any encountered stowconfig.
```

## .stowconfig structure, tips & tricks
The first section is always the `[ignore]` section, as implied by the lack of header.
The second section `[redirect]` is inferred from the explicit header. 

Comments are allowed after a newline; they cannot be inlined.

Syntax for `redirect` entries must match the following regex to be valid: `\"?(.+)\"?\s+(:::)\s+\"?(.+)\"?`
The redirect destination **must** be a directory. 

## planned features
- [ ] negative `[ignore]` section entries, e.g. `!.don't_exclude_me`
- [ ] profile-specific sections, e.g. `[profilename:::ignore]`

## Limitations
### Redirects apply to directory destinations only
Targets for `redirect` entries **must** be directories, they cannot be files.

The limitation has to do with being unable to resolve if a specific redirect is supposed to be a rename of a
specific file, or just a move. 

This is a semantic limitation, and this will not be resolved.

## Supported platforms
GNU/Linux only.
