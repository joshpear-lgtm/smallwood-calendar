# Smallwood school → Skylight

Status: built and tested against the live school website on 6 October 2026. Not yet deployed or connected to a Skylight device.

This bridge publishes three automatically refreshed calendar subscription files. GitHub runs it in the cloud every six hours, so no home computer stays on. A public GitHub repository and GitHub Pages provide free hosting; no Google Calendar or Skylight credentials are needed by the bridge.

## One-time deployment

1. Create a public GitHub repository named `smallwood-calendar` on your own account. Only public school data and bridge code are published; do not add family details or passwords.
2. Upload this folder's contents, including `.github/workflows/sync.yml`, to its `main` branch. A Git upload is needed to preserve the hidden workflow folder.
3. In repository Settings → Pages, choose **GitHub Actions** as the publishing source.
4. In Settings → Actions → General, enable **Read and write permissions** for workflows if the account does not already allow them.
5. In Actions, select **Refresh Smallwood calendars** → **Run workflow**. Check that the refresh and deployment finish successfully.
6. The resulting subscription URLs will be:
   - `https://YOUR-USERNAME.github.io/smallwood-calendar/whole-school.ics`
   - `https://YOUR-USERNAME.github.io/smallwood-calendar/year-5.ics`
   - `https://YOUR-USERNAME.github.io/smallwood-calendar/year-6.ics`
7. In Skylight: My Skylight → Synced Calendars → Sync new calendar → Calendar URL. Add each URL once, then associate Year 5 and Year 6 with the appropriate profiles and Whole School with the family.
8. Confirm that **Parents Evening, 13 October 2026, 15:30 UK time**, **Beech Little Moreton Hall trip, 21 October 2026, 10:30**, and the **Christmas performance, 10 December** appear as expected. Those were present in the source when tested. Changes may happen after this report.

These example URLs are placeholders until deployment; local `.ics` files are previews, not automatic subscriptions.

## What the investigation found

`https://www.smallwood.cheshire.sch.uk/events` contains all 1,961 event records in an inline JSON `eventSources` array used by FullCalendar. No separate AJAX/API request is needed. The two class pages are `/events/9523/2919` (Beech) and `/events/9523/2920` (Hazel). Nine filtered category pages are checked to distinguish school-wide events from other classes.

The “Whole School” page is an aggregate, not a pure school-wide feed. Events assigned to the school-wide category appear only on the master page. Some unclassified records appear in every filtered page, including Beech PE/Forest School and unrelated Ash PE. For those shared records the bridge uses explicit class/year names in the title. It excludes explicit other-class events, sends Beech/Hazel events to their respective feed, and sends events shared by both boys to Whole School once. Generic events shared universally are kept in Whole School. This is a documented inference from the observed data; ambiguous titles cannot be classified perfectly if the school miscategorises them.

## Automatic behaviour

- Stable UID from the school's numeric event ID, independent of title or date.
- Changed records retain their UID, increment SEQUENCE and update LAST-MODIFIED.
- Removed records disappear from the published subscription. Skylight's handling of removals still needs device verification.
- Includes events from the previous 90 days and all available future events, including ongoing multi-day events.
- Interprets published clock times in Europe/London, including daylight saving. Midnight date-only spans use inclusive School Spider end dates converted to exclusive ICS dates. Equal/missing timed ends are omitted rather than inventing a duration.
- The site's old FullCalendar defaults every record to all-day visually despite storing clock times. This bridge preserves non-midnight clock times from the JSON. School mistakes in times or holiday recurrence are preserved; it does not invent corrections.
- Failed fetches or changed page formats fail the run before publication, leaving the last successful hosted feeds available. A format change requires maintenance.
- Each successful run saves feed data and a status timestamp to the repository. This maintains repository activity; GitHub otherwise disables public schedules after 60 days of inactivity. Prolonged failures still require attention.
- GitHub schedules can be delayed; Skylight also controls how often it reads subscriptions. Six hours is the bridge's intended refresh interval, not an end-to-end delivery guarantee.
- `status.json` records the last successful refresh. GitHub can notify the account owner about failed Actions runs according to their notification settings.

## Verification

Six automated tests cover routing, changed-format rejection, summer/winter UK times, stable IDs and revisions, removal, all-day end dates, invalid timed durations, UTF-8 line folding, and failure preservation. All passed. A live refresh fetched all ten pages and generated three feeds, which were independently parsed using the `icalendar` library. No school login is used.

The snapshot contains 28 Whole School, 48 Year 5 and 2 Year 6 records including the previous 90 days. This is not a claim that only two Year 6 activities exist: events shared by both boys are included in Whole School, and the source may be incomplete.

Hosted execution, public feed fetching and Skylight import/update/removal are pending account access and deployment.

## Sources

- School calendar: https://www.smallwood.cheshire.sch.uk/events
- Skylight subscription instructions: https://skylight.zendesk.com/hc/en-us/articles/4416124481819-Syncing-subscribed-calendars-using-the-Skylight-app
- Free GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- Actions pricing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Scheduled workflow limits: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
