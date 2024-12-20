# Gradescope Exporter

`gsout` exports your Gradescope submissions by scraping them off
its website.

Download CLI and run it.

```bash
# Optional: Create and Enable a Python virtual environment.
python3 -m venv .venv && . .venv/bin/activate
# Required: Download the CLI from PyPI.
python3 -m pip install git+https://github.com/henryleberre/gsout.git@master
# Required: Run the CLI.
python3 -m gsout --output  my_export.zip                \
                 --token   '<your signed_token cookie>' \
                 --session '<your _gradescope_session cookie>'
```

In the above example, a `my_export.zip` archive will be created to host your exported files.
This requires your login cookies.

> [!TIP]
> You can find your `_gradescope_session` and `signed_token`
> cookies while logged into [Gradescope](https://www.gradescope.com/)
> with your favorite browser.
>
> - Chromium: DevTools ("Inspect") > Application > Storage > Cookies > https://gradescope.com.
> - Firefox: Inspect > Storage > Cookies > https://gradescope.com.

### Limitations & Contributing

This tool was written quickly to export (most) of my own submissions.
As a result, it is missing many features. A short list of known limitations
is below:

- Only downloads one submission per assignment (the default one when clicking on an assignment link from the course page).
- Does not extract submission metadata (group members, time/date, ...).
- Some others...

Contributions are welcome!

### Privacy & Security

This is a hobby project, unaffiliated with Gradescope.

Please review `gsout`'s source code before running it, at your own risk.

### License

This project is licensed under the [Mozilla Public License Version 2.0](LICENSE).
