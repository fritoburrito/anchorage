# GitHub Pages RSS starter

This is a simple starter repo for hosting your own RSS feed on GitHub Pages.

## Files

- `index.html` - a basic homepage
- `feed.xml` - your RSS feed

## Publish it on GitHub Pages

1. Sign in to GitHub.
2. Create a new public repository.
3. Upload `index.html`, `feed.xml`, and this `README.md` to the repository.
4. Open the repository on GitHub.
5. Go to **Settings** > **Pages**.
6. Under **Build and deployment**, choose **Deploy from a branch**.
7. Choose branch **main** and folder **/(root)**, then save.
8. Wait a minute or two for GitHub Pages to publish.

Your site URL should look like:

`https://YOUR-GITHUB-USERNAME.github.io/YOUR-REPO-NAME/`

Your feed URL should look like:

`https://YOUR-GITHUB-USERNAME.github.io/YOUR-REPO-NAME/feed.xml`

## What to edit before publishing

In `feed.xml`, replace:

- `YOUR-GITHUB-USERNAME`
- `YOUR-REPO-NAME`
- feed title
- descriptions
- sample item links and dates

## How to add a new item

Copy one of the `<item>` blocks in `feed.xml`, paste it above the older items, and update:

- `<title>`
- `<link>`
- `<guid>`
- `<pubDate>`
- `<description>`

Keep the newest item first.

## Notes

- RSS readers usually prefer stable GUIDs.
- Use GMT in `pubDate` and `lastBuildDate`.
- After editing the feed, commit and push your changes to GitHub. GitHub Pages will republish the site automatically.
