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
- Conditional cases, supported through `if-directives`
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
Now, lets try to exclude our `.*rc` files located in `./scripts`.
Update `.stowconfig` so that it looks like the following & rerun with `../pstow.py --target ~ status`:
```stowconfig
*.md
.git/
manpages/
.config/
scripts/
!!scripts/.*rc
```
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
───> scripts/
───────> .bashrc
───────> .jwmrc
───────> .nanorc
───────> .vimrc
───────> .zshrc
WARNING: Aborting.
```
We have successfully un-ignored our .*rc files! \
Keep in mind, is that since the file is read top-to-bottom, \
and the evaluations are being done on a line-by-line basis, \
if you write the un-ignore line before the ignore declaration, the file won't be unignored. 
The following step is to move them to the root dotfile directory. 

Typically, people recommend a bare git repo, but that couples the dotfile structure to the filesystem structure.
This makes things coupled, and difficult to keep track of; most people end up with endless nestings, when they just want
a couple of files, 3 or 4 paths deeper, or a file one level up.

We're going to learn about redirects, also referred at as virtual files. 
Let's start by adding a redirect section! Update your .stowconfig so that it looks like this & rerun as usual:
```stowconfig
*.md
.git/
manpages/
.config/
scripts/
!!scripts/.*rc

[redirect]
scripts/.*rc ::: .
```
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
───> .bashrc
───> .jwmrc
───> .nanorc
───> .vimrc
───> .zshrc
WARNING: Aborting
```
As you can see, we have `[redirect]`ed every `.*rc` file one level up, the same level as the `.stowconfig`, \
denoted by the dot (`.`) \
**Files cannot be renamed this way, only moved.** This is a hard limitation; you cannot change the destination name. \
It's always assumed the destination is a directory, and will be created on demand if it doesn't exist, when applying pstow.

Suppose we have a case, we're going to use a firefox `user.js` config file as a real world scenario,
where we know what the path's going to look like, but since the directory name is automatically generated,
we cannot pinpoint a redirect to any specific path. \
To solve this problem, globbable redirects have been added. \
The path will be inferred by the target we set, so for the following step, make sure the following path exists:
`~/.mozilla/firefox/*.default-release*/`

Let's edit our .stowconfig again; we'll redirect the `.jwmrc` to the mozilla config directory:
```
*.md
.git/
manpages/
.config/
scripts/
!!scripts/.*rc

[redirect]
scripts/.*rc ::: .
scripts/.jwmrc ::: .mozilla/firefox/*.default-release*/
```
```bash
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
───> .bashrc
───> .nanorc
───> .vimrc
───> .zshrc
───> .mozilla/
───────> firefox/
───────────> h2rjlo7a.default-release/
───────────────> .jwmrc
WARNING: Aborting.
```
Success! We can dynamically redirect anything we want, however deep we want, with full support for multiple targets. \
If we wanted to be a little more generous, and insert our file in every directory inside the firefox dir, \
here's how we'd do that:
```stowconfig
*.md
.git/
manpages/
.config/
scripts/
!!scripts/.*rc

[redirect]
scripts/.*rc ::: .
scripts/.jwmrc ::: .mozilla/firefox/*.default-release*/
```
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
───> .bashrc
───> .nanorc
───> .vimrc
───> .zshrc
───> .mozilla/
───────> firefox/
───────────> Crash Reports/
───────────────> .jwmrc
───────────> Pending Pings/
───────────────> .jwmrc
───────────> installs.ini/
───────────────> .jwmrc
───────────> h2rjlo7a.default-release/
───────────────> .jwmrc
───────────> profiles.ini/
───────────────> .jwmrc
───────────> zhqudbkl.default/
───────────────> .jwmrc
WARNING: Aborting.
```
Now, we'll start dealing with one of the last topics regarding `.stowconfig`: `if-directives`.
As of writing, there are four possible directives:
- `if-pkg`
- `if-not-pkg`
- `if-profile`
- `if-not-profile`

The first directive checks for the existence of packages in non-interactive `$PATH`. \
A subshell is *never* opened, so it's (probably) secure to be as wack as you want. \
You can include multiple packages to check. \
The second directive checks the inverse, i.e. the absence of packages in `$PATH`. \
The third directive checks the current active `profile`, and runs it is. \
The fourth directive checks the current active `profile`, and runs if it isn't.
Here's some example usage; update your `.stowconfig` to look like this, & run as usual:
```stowconfig
*.md
.git/
manpages/
.config/
scripts/
!!scripts/.*rc
[if-not-pkg:::nano]
    scripts/.nanorc
[end]
[if-not-pkg:::vim]
    scripts/.vimrc
[end]
[if-pkg:::zsh some-other-package]
    !!scripts/.zshrc
[end]

[redirect]
scripts/.*rc ::: .
scripts/.jwmrc ::: .mozilla/firefox/*/
```
```bash
 ~/.../dotfiles (changes) $ ../pstow.py --target ~ status
WARNING: Couldn't fulfill condition for [if-not-pkg:::nano]. Skipping block contents...
Applying [if-not-pkg:::vim] entry: scripts/.vimrc
WARNING: Couldn't fulfill condition for [if-pkg:::zsh some-other-package]. Skipping block contents...
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
───> .bashrc
───> .nanorc
───> .zshrc
───> .mozilla/
───────> firefox/
───────────> Crash Reports/
───────────────> .jwmrc
───────────> Pending Pings/
───────────────> .jwmrc
───────────> installs.ini/
───────────────> .jwmrc
───────────> pkziaq2y.default-release/
───────────────> .jwmrc
───────────> profiles.ini/
───────────────> .jwmrc
───────────> xpqxabjk.default/
───────────────> .jwmrc
WARNING: Aborting.
```
As you can see, since I don't have `vim` on my `$PATH`, `.vimrc` is automatically ignored! \
Of course, `nano` exists, but `.zhrc` AND `some-other-package` do not, so their rules are not applied.

Finally, we'll talk about profiles & their directives.

Suppose I wouldn't want my `.jwmrc` config file in the firefox directories when deploying this on my work partition or PC.
Let's edit our .stowconfig accordingly:
```stowconfig
*.md
.git/
manpages/
.config/
scripts/
!!scripts/.*rc
[if-not-pkg:::nano]
    scripts/.nanorc
[end]
[if-not-pkg:::vim]
    scripts/.vimrc
[end]
[if-pkg:::zsh some-other-package]
    !!scripts/.zshrc
[end]

[redirect]
scripts/.*rc ::: .

[if-not-profile:::work]
    scripts/.jwmrc ::: .mozilla/firefox/*/
[end]
```

...and run like this, setting the current profile in the process:
```bash
 ~/.../dotfiles (changes) $ ../pstow.py --profile work --target ~ status
WARNING: Couldn't fulfill condition for [if-not-pkg:::nano]. Skipping block contents...
Applying [if-not-pkg:::vim] entry: scripts/.vimrc
WARNING: Couldn't fulfill condition for [if-pkg:::zsh some-other-package]. Skipping block contents...
WARNING: Couldn't fulfill condition for [if-not-profile:::work]. Skipping block contents...
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
───> .bashrc
───> .jwmrc
───> .nanorc
───> .zshrc
WARNING: Aborting.
```
When running with `--profile work`, the `.jwmrc` won't be applied, meaning we can keep one configuration file for \
multiple deployments in different systems!

This concludes the entire tutorial regarding `pstow`; next step is looking at the `--help` prompt, and checking out \
deployments in production. A good starter for the latter would be [my personal dotfiles](https://github.com/gerelef/dotfiles).

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

## .stowconfig exhaustive structure
The first section is always the `[ignore]` section, as implied by the lack of header. \
The second section `[redirect]` is inferred from the explicit header.

"Unignores" should be evaluated after a file has been ignored, otherwise they will *not* apply. 
They're evaluated as-is; no reordering happens on any level, so the onus is on you to make sure they work right.

Comments are allowed after a newline; they cannot be inlined.

Syntax for `redirect` entries must match the following regex to be valid: `\"?(.+)\"?\s+(:::)\s+\"?(.+)\"?`
The redirect destination **must** be a directory. This is a semantic limitation, and will not be raised.

Profile is considered `default` if omitted.

The following is the exhaustive syntax of a .stowconfig file:
```stowconfig
// [ignore] header is not necessary, implied by the lack of header at the start of the file
*.md
.stowconfig
.git/

scripts/*

[if-profile:::work hobby]
    // unignore work config
    !!scripts/.mywork
    // unignore all hobby dotfiles
    !!scripts/*hobby*
[end]
[if-not-profile:::default]
    // if on any other profile other than default, ignore the .someThing file  
    .config/.someThing
[end]
// if vim and nano are currently installed, symlink their files
[if-pkg:::vim nano]
    !!scripts/.vimrc 
    !!scripts/.nanorc
[end]
[if-not-pkg:::delta]
    // if git-delta is not currently installed, go ahead and ignore it's .gitconfig
    scripts/.gitconfig-gitdelta
[end]

[redirect]
myfile ::: .
some/other/file ::: some/

[if-profile:::testing]
    testing/* ::: something/else/*/
[end]
```

More details on `if-directives`:
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

## Supported platforms
GNU/Linux only.
