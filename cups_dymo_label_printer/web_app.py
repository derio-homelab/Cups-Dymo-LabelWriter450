"""
Flask web application for Dymo label printing.

Provides a web interface for designing and printing labels.
"""

from io import BytesIO
import base64
import json
import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file

from .config import LABEL_SIZES, DEFAULT_LABEL_SIZE, DEFAULT_FONT_SIZE
from . import fonts, images
from .document import LabelDoc, TextBlock, ImageBlock, canvas_mm, from_flat, pt_to_px
from .label_generator import render
from .printer_service import PrinterService


UPLOAD_OVERHEAD_BYTES = 64 * 1024  # multipart framing on top of the file itself

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = images.max_upload_bytes() + UPLOAD_OVERHEAD_BYTES
printer_service = PrinterService()
_MEMORY_FILE = os.getenv('LABEL_MEMORY_FILE', 'saved_labels.json')
_saved_labels: list[dict] = []  # in-memory stack of saved labels


def _label_key(payload: dict) -> tuple:
    """Generate a hashable key for deduplication of saved labels."""
    return (
        payload.get('text', ''),
        payload.get('label_size', DEFAULT_LABEL_SIZE),
        int(payload.get('font_size', DEFAULT_FONT_SIZE)),
        payload.get('align', 'center'),
        int(payload.get('copies', 1)),
    )


def _save_label(payload: dict) -> dict:
    """Save label payload to stack, deduplicating and moving to top."""
    global _saved_labels
    key = _label_key(payload)
    # Remove any existing matching entry
    _saved_labels = [entry for entry in _saved_labels if _label_key(entry) != key]
    new_entry = {
        'id': str(uuid.uuid4()),
        'text': payload.get('text', ''),
        'label_size': payload.get('label_size', DEFAULT_LABEL_SIZE),
        'font_size': int(payload.get('font_size', DEFAULT_FONT_SIZE)),
        'align': payload.get('align', 'center'),
        'copies': int(payload.get('copies', 1)),
    }
    _saved_labels.insert(0, new_entry)
    _persist_memory()
    return new_entry


def _delete_labels(ids: list[str]) -> None:
    """Delete labels by id from the saved stack."""
    global _saved_labels
    id_set = set(ids)
    _saved_labels = [entry for entry in _saved_labels if entry['id'] not in id_set]
    _persist_memory()


def _persist_memory() -> None:
    try:
        with open(_MEMORY_FILE, 'w', encoding='utf-8') as fh:
            json.dump(_saved_labels, fh)
    except Exception:
        # Fail-soft on persistence errors
        pass


def _load_memory() -> None:
    global _saved_labels
    if not _MEMORY_FILE or not os.path.exists(_MEMORY_FILE):
        _saved_labels = []
        return
    try:
        with open(_MEMORY_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            if isinstance(data, list):
                _saved_labels = data
    except Exception:
        _saved_labels = []


_load_memory()


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


def _flat_for_history(doc: LabelDoc, copies: int) -> dict:
    """Flat v1 view of a document, for the (unchanged this phase) history stack."""
    texts = [b for b in doc.blocks if isinstance(b, TextBlock)]
    first = texts[0] if texts else None
    return {
        'text': '\n'.join(b.text for b in texts),
        'label_size': doc.label_size,
        'font_size': pt_to_px(first.font_size_pt, 300) if first else DEFAULT_FONT_SIZE,
        'align': first.align if first else 'center',
        'copies': copies,
    }


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
    return send_file(path, mimetype=mimetype)


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


@app.route('/print', methods=['POST'])
def print_label():
    """Print a label from a document (``{doc, copies}``) or the old flat payload."""
    try:
        data = request.json
        doc = _doc_from_request(data)
        copies = int(data.get('copies', doc.copies))

        if not _has_content(doc):
            return jsonify({'success': False, 'error': 'No text provided'}), 400

        result = render(doc)
        for block in result.blocks:
            if block['missing']:
                return jsonify({
                    'success': False,
                    'error': f"Image missing for block {block['id']}",
                }), 400

        job_id = printer_service.print_image(result.image, doc.label_size, copies, 'Label')

        # Save to memory stack (dedup + move to top)
        _save_label(_flat_for_history(doc, copies))

        return jsonify({
            'success': True,
            'message': f'Print job {job_id} submitted successfully',
            'job_id': job_id
        })

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


@app.route('/memory', methods=['GET', 'DELETE'])
def memory():
    """Manage in-memory saved labels stack."""
    if request.method == 'GET':
        return jsonify(_saved_labels)

    # DELETE selected ids
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if not isinstance(ids, list):
        return jsonify({'success': False, 'error': 'ids must be a list'}), 400
    _delete_labels([str(i) for i in ids])
    return jsonify({'success': True, 'remaining': _saved_labels})


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
