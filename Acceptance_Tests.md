# Acceptance Tests

These scenarios describe the expected, user-visible behaviors of the LabelWriter 450 web printer. Implement them with TDD (red/green/refactor) and keep this file in sync with the shipped features.

## Label Generation

### Should render default label with correct dimensions

- Given text `Hello World`
- And default label size `11354`
- When creating a label image
- Then the image mode is `RGB`
- And the pixel dimensions equal the configured mm size converted at DPI 300
- And the background pixels are white

### Should support all configured label sizes

- Given any label code in `{11354, 30252, 30323, 30256, 99012}`
- When creating a label image with that code
- Then the image width and height match the mm dimensions at DPI 300
- And the label size maps to its CUPS media code as defined in `LABEL_SIZES`

### Should reject unknown label sizes

- Given label size `INVALID`
- When creating a label image
- Then a `ValueError` is raised with message `Unknown label size: INVALID`

### Should align text left, center, and right

- Given text `Align Me`
- When creating labels with `align` set to `left`, `center`, and `right`
- Then a label image is produced for each alignment without errors
- And the text bounding box stays within the image bounds

## Printer Service

### Should build correct CUPS options and submit print job

- Given a PIL image and label size `11354`
- And copies set to `2`
- When calling `PrinterService.print_image`
- Then it rotates the image 90° when its aspect differs from the media's (`wNNNhNNN`)
- And saves a temporary PNG
- And calls `cups.Connection.printFile` with options `media=w162h90`, `fit-to-page=True`, `orientation-requested=3`, `copies=2`
- And removes the temporary file after submission
- And returns the CUPS job id from `printFile`

### Should reject invalid label size before printing

- Given label size `BAD`
- When calling `PrinterService.print_image`
- Then a `ValueError` is raised and no CUPS call is made

### Should surface CUPS failures as runtime errors

- Given `cups.Connection.printFile` raises an exception
- When calling `PrinterService.print_image`
- Then a `RuntimeError` is raised containing the original failure message

### Should report printer status

- Given a configured printer `dymo` exists
- When calling `get_printer_status`
- Then a printer info dictionary is returned from CUPS
- And if the printer is missing, the response includes `{ "error": "Printer not found" }`

## Flask API

### /preview should return base64 PNG for valid input

- Given JSON `{ "text": "Hello", "label_size": "11354", "font_size": 40, "align": "center" }`
- When posting to `/preview`
- Then the response status is 200
- And `success` is true
- And `image` is a data URL starting with `data:image/png;base64,`

### /preview should return 400 for invalid label size

- Given JSON `{ "text": "Hello", "label_size": "BAD" }`
- When posting to `/preview`
- Then the response status is 400
- And `success` is false with an error mentioning `Unknown label size`

### /print should submit job and return job id

- Given JSON `{ "text": "Print Me", "label_size": "11354", "font_size": 40, "align": "center", "copies": 1 }`
- And `PrinterService.print_image` is mocked to return `123`
- When posting to `/print`
- Then the response status is 200
- And `success` is true
- And `job_id` equals `123`
- And the message mentions the submitted job id

### /print should reject empty text with 400

- Given JSON `{ "text": "", "label_size": "11354" }`
- When posting to `/print`
- Then the response status is 400
- And `success` is false with error `No text provided`

### /print should reject invalid label size with 400

- Given JSON `{ "text": "Hello", "label_size": "BAD" }`
- When posting to `/print`
- Then the response status is 400
- And `success` is false with an error mentioning `Unknown label size`

### /print should surface CUPS failures with 500

- Given JSON `{ "text": "Hello", "label_size": "11354" }`
- And `PrinterService.print_image` raises `RuntimeError("Failed to print: connection error")`
- When posting to `/print`
- Then the response status is 500
- And `success` is false with error `Failed to print: connection error`

### /status should return printer info

- When calling `GET /status`
- Then the response status is 200
- And the body contains either the printer info dictionary from CUPS or an `error` field

## Fonts

### Should list the curated font families found on the host

- Given font files in `LABEL_FONT_DIRS`
- When `/fonts` is requested
- Then each catalog family with at least one file is listed with its available styles
- And a family with no file is omitted

### Should mix fonts, sizes and styles on one label

- Given a label with several text blocks
- When each block sets its own family, size in points, bold, italic, underline and alignment
- Then the render shows every block in its own style
- And a style the family lacks renders as the nearest available one, and the editor disables that toggle

## Images

### Should add uploaded images and built-in icons

- Given a PNG, JPEG or SVG up to `LABEL_MAX_UPLOAD_MB`, or an icon from `/icons`
- When the user uploads it or picks the icon
- Then an image block is added, rendered pure black and white with the chosen threshold or dither mode
- And a larger file is refused with 413 and any other type with 400

## Live preview

### Should show the render inside a frame of the stock's real shape

- Given a label stock and orientation
- When the user types or changes any setting
- Then after about 250 ms the server render appears inside a rounded frame of that aspect ratio
- And a block that overflows the label gets a red outline and a message

### Should edit, move and scale blocks on the label

- Given blocks on the preview
- When the user clicks a text block, drags a block, drags an image's corner handle or presses an arrow key
- Then the text is edited in place (Esc cancels), the block moves with at least 1 mm kept on the label,
  the image scales between 2 mm and the label width, and each arrow press nudges 0.5 mm

## Orientation

### Should swap the canvas and print the way it is previewed

- Given a label in portrait or landscape
- When the user toggles the orientation
- Then the canvas swaps its width and height, and the orientation is saved with the label
- And the printed image is rotated to the stock's media so it matches the preview

## History

### Should store printed labels without duplication

- Given a design printed from the editor
- When `/print` succeeds
- Then the design is saved, or the existing entry with identical content is bumped (`last_printed_at`, `print_count`)
- And re-printing from history bumps that entry instead of adding one

### Should list saved labels with thumbnails, search and sort

- Given saved labels
- When the history panel is open
- Then each label shows a renderer-made thumbnail, name and last-printed time
- And search matches names and text, and sort is by last printed, created or name
- And the panel can be collapsed and expanded without losing its contents

### Should allow selecting a saved label to re-fill the editor

- Given a saved label in the panel
- When the user presses Open
- Then the editor shows its blocks, stock, orientation, copies and name, marked "Editing: name"

### Should allow duplicate, re-print and delete

- Given saved labels with checkboxes and a select-all
- When the user presses Duplicate, Re-print, or Delete selected
- Then Duplicate adds an unstarred copy, Re-print prints without opening and bumps the entry
- And Delete removes exactly the selected labels, and select-all selects every label

## Stars

### Should keep starred labels first

- Given a star toggle on each label and a Starred only filter
- When the user stars a label
- Then it moves above the unstarred labels under every sort, and the state persists
- And Starred only lists just the starred labels

## General UX

### Should give keyboard shortcuts and feedback

- Given the designer page
- When the user presses Ctrl/Cmd+Enter or Ctrl/Cmd+P
- Then the label is printed, or re-rendered without the browser print dialog
- And toasts report print success, failure and history warnings, and a badge shows the printer status

### Should work on a phone, in dark mode, and remember settings

- Given a 360 px wide screen or a dark system scheme
- When the page loads
- Then it has no horizontal scroll and follows the scheme, with a manual theme toggle
- And the copies stepper is limited to 1-99
- And the last stock, font and orientation are restored after a reload

## Persistence (Saved Labels on Disk)

### Should persist saved labels to disk after print/delete

- Given a successful `/print` call that adds to the history
- When the history is written to disk as JSON
- Then the file contains `{"version": 2, "labels": [...]}` with ids and blocks
- And when labels are deleted via `/labels` DELETE, the file is updated accordingly

### Should load saved labels from disk on startup

- Given a JSON persistence file with saved labels
- When the app starts (or the module is reloaded)
- Then `/labels` returns the entries from disk, starred first, then in the active sort (default last printed)

## Container / Runtime

### Should start Flask and CUPS with configured admin password

- Given `.env` contains `CUPS_ADMIN_PASSWORD`
- When running `docker compose up --build -d`
- Then the CUPS admin UI is reachable on port 631 with user `cupsadmin`
- And the Flask app is reachable on port 5000 serving the label UI
- And the default printer name is `dymo`
