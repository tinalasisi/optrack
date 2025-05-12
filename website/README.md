# OpTrack Dashboard

This is a simple React dashboard for the OpTrack system. It displays the current status of grant databases, including counts, storage metrics, and other statistics.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```

3. Build for production:
   ```bash
   npm run build
   ```

## Automated Data Updates

The dashboard reads its data from a JSON file located at `public/sample-data.json`. This file should be regularly updated with fresh statistics from the OpTrack system.

To update the data automatically:

```bash
./update-stats.sh
```

This script:
1. Runs the OpTrack `stats.py` script to generate fresh statistics
2. Saves the output to the dashboard's data file
3. Optionally rebuilds the website if npm is installed

## GitHub Pages Integration

To host this dashboard on GitHub Pages:

1. Build the website:
   ```bash
   npm run build
   ```

2. Push the `build` directory to the `gh-pages` branch of your repository:
   ```bash
   npm install -g gh-pages
   gh-pages -d build
   ```

Or add this to your package.json:
```json
"scripts": {
  "deploy": "gh-pages -d build"
}
```

Then run:
```bash
npm run deploy
```

## Customization

- Edit `src/App.js` to modify the dashboard layout and components
- Edit `src/index.css` to change styles
- The data format must match the output of the OpTrack `stats.py` script