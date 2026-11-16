## Dashboard Studio

Splunk stores a Studio dashboard as XML that wraps the Studio JSON definition:

```xml
<dashboard version="2" theme="dark">
  <label>Title</label>
  <definition><![CDATA[ { ...Studio JSON... } ]]></definition>
</dashboard>
```

`splunk.singlevalue` rounds to a whole number unless `options.numberPrecision` is set to a number of decimal places, for example `"numberPrecision": 2` (a number, not a string). Set it for values with decimals, such as a rate under 1%.

Keep the definition in a `.json` file, write the wrapper next to it as `.xml` with your file-editing tool (not a script), and deploy the XML with `splunkctl dashboard add <name> --file <name>.xml --app search`.
