# sneferu.ai

The production repository for [sneferu.ai](https://sneferu.ai/).

## Release path

`main` is the only publishing branch. Every push builds a clean public artifact,
checks its pages, links, media, contact form, custom domain, and file limits, and
deploys to GitHub Pages only after those checks pass. Pull requests run the same
build and validation without publishing.

The GitHub Pages artifact deliberately excludes this README, repository tooling,
and workflow files. It preserves the public `research/` archive, `CNAME`, and
`.nojekyll`.
