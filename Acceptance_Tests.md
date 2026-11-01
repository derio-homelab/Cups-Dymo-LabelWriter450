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
- Then it saves a temporary PNG
- And calls `cups.Connection.printFile` with options `media=w162h90`, `fit-to-page=True`, `copies=2`
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

## Memory (Saved Labels)

### Should store printed labels as previews without duplication

- Given a label payload `{ text, label_size, font_size, align, copies }`
- When `/print` is called successfully
- Then the label is added to the saved stack as a preview
- And if an identical label already exists, the old entry is removed and the new one is placed at the top (no duplicates)

### Should allow expand/collapse of the saved stack

- Given the saved labels section
- When the user collapses or expands it
- Then the stack hides or shows without losing its contents

### Should allow selecting a saved label to re-fill the form

- Given a saved label in the stack
- When the user selects that saved label
- Then the main input fields are populated with that label’s text, label_size, font_size, align, and copies

### Should allow deleting a saved label

- Given a saved label in the stack
- When the user deletes that saved label
- Then it is removed from the stack
- And it is no longer available for selection or duplication checks

### Should allow selecting multiple labels and deleting them at once

- Given each saved label has a checkbox
- And a Delete action is available
- When the user checks multiple labels and presses Delete
- Then all selected labels are removed from the stack
- And the remaining labels stay intact in order

### Should allow select-all from the stack header

- Given a select-all checkbox at the stack level
- When the user toggles select-all on
- Then all saved labels become selected
- And pressing Delete removes all labels
- And toggling select-all off clears all selections without deleting

## Persistence (Saved Labels on Disk)

### Should persist saved labels to disk after print/delete

- Given a successful `/print` call that adds to the stack
- When the stack is written to disk as JSON
- Then the file contains the saved labels (including ids and fields)
- And when labels are deleted via `/memory` DELETE, the file is updated accordingly

### Should load saved labels from disk on startup

- Given a JSON persistence file with saved labels
- When the app starts (or the module is reloaded)
- Then `/memory` returns the entries from disk in stack order (most recent first)

## Container / Runtime

### Should start Flask and CUPS with configured admin password

- Given `.env` contains `CUPS_ADMIN_PASSWORD`
- When running `docker compose up --build -d`
- Then the CUPS admin UI is reachable on port 631 with user `cupsadmin`
- And the Flask app is reachable on port 5000 serving the label UI
- And the default printer name is `dymo`
