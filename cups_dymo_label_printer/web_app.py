"""
Flask web application for Dymo label printing.

Provides a web interface for designing and printing labels.
"""

from io import BytesIO
import base64
import logging
import os
from typing import Optional

from flask import Flask, render_template, request, jsonify, send_file

from .config import LABEL_SIZES
from . import fonts, images
from .document import LabelDoc, TextBlock, ImageBlock, canvas_mm, from_flat
from .label_generator import render
from .printer_service import PrinterService
from .store import DEFAULT_SORT, LabelNotFound, LabelStore, StoreError, doc_of, flat_fields


UPLOAD_OVERHEAD_BYTES = 64 * 1024  # multipart framing on top of the file itself

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = images.max_upload_bytes() + UPLOAD_OVERHEAD_BYTES
printer_service = PrinterService()
_MEMORY_FILE = os.getenv('LABEL_MEMORY_FILE', 'saved_labels.json')
store = LabelStore(_MEMORY_FILE)
log = logging.getLogger(__name__)
THUMBNAIL_DPI = 100
HISTORY_WARNING = 'Printed, but the label history could not be updated'


@app.route('/')
def index():
    """Render the main label design page."""
    return render_template('index.html', label_sizes=LABEL_SIZES)


@app.errorhandler(413)
def _too_large(_error):
    return jsonify({'success': False, 'error': 'Upload is too large'}), 413


def _doc_from_request(data: dict, default_text: str = '') -> LabelDoc:
    """Build a document from a doc payload (``{doc}`` or bare) or a v1 flat payload."""
    if not isinstance(data, dict):
        raise ValueError('Request body must be a JSON object')
    raw = data.get('doc', data if 'blocks' in data else None)
    if raw is not None:
        return LabelDoc.from_json(raw)
    return from_flat({**data, 'text': data.get('text', default_text)})


def _png_data_url(image) -> str:
    buffered = BytesIO()
    image.save(buffered, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffered.getvalue()).decode('utf-8')


def _has_content(doc: LabelDoc) -> bool:
    return any(
        isinstance(b, ImageBlock) or (isinstance(b, TextBlock) and b.text.strip())
        for b in doc.blocks
    )


@app.route('/fonts', methods=['GET'])
def list_fonts():
    """List the curated font families found on this host."""
    return jsonify(fonts.list_fonts())


@app.route('/icons', methods=['GET'])
def list_icons():
    """List the built-in icons."""
    return jsonify(images.list_icons())


@app.route('/images', methods=['POST'])
def upload_image():
    """Store an uploaded PNG, JPEG or SVG; returns its reference."""
    upload = request.files.get('file')
    if upload is None:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    try:
        ref = images.store_upload(upload.read(), upload.filename or '')
    except images.ImageTooLarge as e:
        return jsonify({'success': False, 'error': str(e)}), 413
    except images.UnsupportedImage as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'ref': ref})


@app.route('/images/<name>', methods=['GET'])
def get_image(name: str):
    """Serve a stored upload."""
    try:
        path = images.upload_path(name)
    except images.ImageMissing:
        return jsonify({'success': False, 'error': 'Image not found'}), 404
    mimetype = {'png': 'image/png', 'jpg': 'image/jpeg', 'svg': 'image/svg+xml'}[name.rsplit('.', 1)[1]]
    response = send_file(path, mimetype=mimetype)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = (
        "default-src 'none'; style-src 'unsafe-inline'; sandbox")
    if mimetype == 'image/svg+xml':
        response.headers['Content-Disposition'] = 'attachment'
    return response


@app.route('/render', methods=['POST'])
def render_label():
    """Render a label document; returns the PNG plus per-block layout results."""
    try:
        doc = _doc_from_request(request.get_json(silent=True) or {})
        result = render(doc)
        width_mm, height_mm = canvas_mm(doc)
        keys = ('id', 'bbox_mm', 'overflow', 'font_substituted', 'missing')
        return jsonify({
            'success': True,
            'image': _png_data_url(result.image),
            'width_mm': width_mm,
            'height_mm': height_mm,
            'blocks': [{k: b[k] for k in keys} for b in result.blocks],
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@app.route('/preview', methods=['POST'])
def preview():
    """
    Compatibility alias: preview a label from the old flat payload (or a doc).

    Returns the image data URL that can be directly used in an <img> src attribute.
    """
    try:
        doc = _doc_from_request(request.json, default_text='Sample Text')
        return jsonify({'success': True, 'image': _png_data_url(render(doc).image)})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


def _render_for_print(doc: LabelDoc):
    """Render ``doc`` for the printer; ValueError (a 400) if it has nothing to print."""
    if not _has_content(doc):
        raise ValueError('No text provided')
    result = render(doc)
    for block in result.blocks:
        if block['missing']:
            raise ValueError(f"Image missing for block {block['id']}")
    return result


def _print_and_record(doc: LabelDoc, label_id: Optional[str], result, saved=None):
    """Print an already-rendered ``doc`` and bump its history entry (R16).

    A history failure after CUPS accepted the job is not a print failure: the
    response still succeeds, with a ``warning`` and the last known entry.
    """
    job_id = printer_service.print_image(result.image, doc.label_size, doc.copies, 'Label')
    body = {
        'success': True,
        'message': f'Print job {job_id} submitted successfully',
        'job_id': job_id,
    }
    try:
        body['label'] = store.record_print(doc, label_id)
    except (StoreError, LabelNotFound):
        log.exception('print job %s submitted but history not updated', job_id)
        body['label'] = saved
        body['warning'] = HISTORY_WARNING
    return jsonify(body)


@app.route('/print', methods=['POST'])
def print_label():
    """Print a document (``{doc, id?, copies}``) or the old flat payload.

    With ``id`` the design is saved over that entry first; if that save fails
    nothing is printed (R16).
    """
    try:
        data = request.json
        doc = _doc_from_request(data)
        doc.copies = int(data.get('copies', doc.copies))
        label_id = data.get('id') or None

        result = _render_for_print(doc)

        saved = None
        if label_id is not None:
            try:
                saved = store.update(str(label_id), doc)
            except LabelNotFound:
                return jsonify({'success': False, 'error': 'Label not found'}), 404
            except StoreError as e:
                return jsonify({'success': False, 'error': str(e)}), 500
            label_id = saved['id']

        return _print_and_record(doc, label_id, result, saved)

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except RuntimeError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500


@app.route('/status', methods=['GET'])
def printer_status():
    """Get the current printer status."""
    status = printer_service.get_printer_status()
    return jsonify(status)


def _with_flat_fields(labels: list) -> list:
    return [{**label, **flat_fields(label)} for label in labels]


@app.route('/memory', methods=['GET', 'DELETE'])
def memory():
    """Compatibility alias of ``/labels``: v2 labels plus the flat v1 fields (R13)."""
    if request.method == 'DELETE':
        try:
            store.delete(_ids_from_request())
        except ValueError as e:
            return _fail(str(e), 400)
        except StoreError as e:
            return _fail(str(e), 500)
        return jsonify({'success': True, 'remaining': _with_flat_fields(store.list())})
    return jsonify(_with_flat_fields(store.list()))


def _fail(error: str, status: int):
    return jsonify({'success': False, 'error': error}), status


def _label_route(handler):
    """Map store/validation errors of a ``/labels`` handler to 404 / 400 / 500."""
    def wrapped(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except LabelNotFound:
            return _fail('Label not found', 404)
        except StoreError as e:
            return _fail(str(e), 500)
        except ValueError as e:
            return _fail(str(e), 400)
        except RuntimeError as e:  # CUPS
            return _fail(str(e), 500)
    wrapped.__name__ = handler.__name__
    return wrapped


def _request_doc() -> LabelDoc:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Request body must be a JSON object')
    return LabelDoc.from_json(data.get('doc', data))


def _json_object() -> dict:
    """The request's JSON body as an object; no body is ``{}``, anything else a 400."""
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError('Request body must be a JSON object')
    return data


def _ids_from_request() -> list:
    ids = _json_object().get('ids', [])
    if not isinstance(ids, list):
        raise ValueError('ids must be a list')
    return [str(i) for i in ids]


@app.route('/labels', methods=['GET'])
@_label_route
def list_labels():
    """Saved labels: ``q`` searches name + text, ``sort``, ``starred`` filters (R13, R15)."""
    starred = request.args.get('starred', '').lower() in ('1', 'true', 'yes')
    labels = store.list(q=request.args.get('q'),
                        sort=request.args.get('sort') or DEFAULT_SORT,
                        starred_only=starred)
    return jsonify({'success': True, 'labels': labels})


@app.route('/labels', methods=['POST'])
@_label_route
def create_label():
    return jsonify({'success': True, 'label': store.create(_request_doc())}), 201


@app.route('/labels', methods=['DELETE'])
@_label_route
def delete_labels():
    return jsonify({'success': True, 'deleted': store.delete(_ids_from_request())})


@app.route('/labels/<label_id>', methods=['GET'])
@_label_route
def get_label(label_id: str):
    return jsonify({'success': True, 'label': store.get(label_id)})


@app.route('/labels/<label_id>', methods=['PUT'])
@_label_route
def update_label(label_id: str):
    """Save over an entry in place, name included (R14, R25)."""
    return jsonify({'success': True, 'label': store.update(label_id, _request_doc())})


@app.route('/labels/<label_id>', methods=['DELETE'])
@_label_route
def delete_label(label_id: str):
    if not store.delete([label_id]):
        raise LabelNotFound(label_id)
    return jsonify({'success': True})


@app.route('/labels/<label_id>/duplicate', methods=['POST'])
@_label_route
def duplicate_label(label_id: str):
    return jsonify({'success': True, 'label': store.duplicate(label_id)}), 201


@app.route('/labels/<label_id>/star', methods=['PUT'])
@_label_route
def star_label(label_id: str):
    starred = _json_object().get('starred')
    if not isinstance(starred, bool):
        raise ValueError('starred must be a boolean')
    return jsonify({'success': True, 'label': store.set_star(label_id, starred)})


@app.route('/labels/<label_id>/print', methods=['POST'])
@_label_route
def reprint_label(label_id: str):
    """Re-print a saved label as stored (optionally with other ``copies``) and bump it."""
    saved = store.get(label_id)
    doc = doc_of(saved)
    data = _json_object()
    try:
        doc.copies = int(data.get('copies', doc.copies))
    except (TypeError, ValueError):
        raise ValueError('copies must be an integer') from None
    return _print_and_record(doc, label_id, _render_for_print(doc), saved)


@app.route('/labels/<label_id>/thumbnail.png', methods=['GET'])
@_label_route
def label_thumbnail(label_id: str):
    """The renderer's output at 100 DPI; a missing image is simply absent (R13)."""
    image = render(doc_of(store.get(label_id)), dpi=THUMBNAIL_DPI).image
    buffered = BytesIO()
    image.save(buffered, format='PNG')
    buffered.seek(0)
    return send_file(buffered, mimetype='image/png')


def run_app(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """
    Run the Flask application.
    
    Args:
        host: Host address to bind to
        port: Port number to listen on
        debug: Enable debug mode
    """
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app()
