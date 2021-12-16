# wwt-hips-list-importer

Create WTML from the canonical HiPS list.

This is a two-stage process. The program `./hips_list_parser.py` downloads the
current HiPS list and updates three files that are stored in this repo:

- `toc.txt` with a terse table-of-contents of all of the datasets;
- `datasets.yml` with the key metadata for input into WWT; and
- `hierarchy.yml` expressing the folder hierarchy into which the datasets should
  be organized

When new HiPS datasets are added, you can look at the diffs to see what's
changed, and manually fix up any metadata issues that need improvement. Note that
this script currently won't do a good job of preserving manual fixes made in
previous runs (`git add -p` is your friend).

Once the metadata are edited, the WTML can be created with `./create_wtml.py`.
This creates a file named `hips.wtml` suitable for upload to the WWT servers.
