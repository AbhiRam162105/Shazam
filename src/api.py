"""
REST API for the Shazam audio recognition system.
Provides endpoints for song identification and database management.
"""

from flask import Flask, request, jsonify, send_file
import tempfile
import os
import logging
from pathlib import Path
from typing import Dict, Any

try:
    from .shazam_system import ShazamSystem
    from .config import API_HOST, API_PORT, API_DEBUG
except ImportError:
    from shazam_system import ShazamSystem
    from config import API_HOST, API_PORT, API_DEBUG

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Initialize Shazam system
shazam = ShazamSystem()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        stats = shazam.get_database_stats()
        return jsonify({
            'status': 'healthy',
            'database_connected': True,
            'total_songs': stats.get('total_songs', 0)
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/identify', methods=['POST'])
def identify_audio():
    """
    Identify audio from uploaded file.
    
    Expects:
        - audio file in request.files['audio']
        
    Returns:
        - JSON with identification result
    """
    try:
        # Check if audio file was uploaded
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            audio_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Identify the audio
            match_result = shazam.identify_audio_file(temp_path)
            
            if match_result:
                result = {
                    'success': True,
                    'match': {
                        'title': match_result.title,
                        'artist': match_result.artist,
                        'album': match_result.album,
                        'confidence': round(match_result.confidence, 3),
                        'matching_hashes': match_result.matching_hashes,
                        'alignment_strength': round(match_result.alignment_strength, 3)
                    }
                }
            else:
                result = {
                    'success': False,
                    'message': 'No match found'
                }
            
            return jsonify(result)
            
        finally:
            # Clean up temporary file
            os.unlink(temp_path)
            
    except Exception as e:
        logger.error(f"Audio identification failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/identify/microphone', methods=['POST'])
def identify_microphone():
    """
    Identify audio from microphone recording.
    
    Expects:
        - JSON with 'duration' (optional, defaults to 10 seconds)
        
    Returns:
        - JSON with identification result
    """
    try:
        data = request.get_json() or {}
        duration = data.get('duration', 10.0)
        
        # Validate duration
        if not isinstance(duration, (int, float)) or duration <= 0 or duration > 30:
            return jsonify({'error': 'Duration must be between 0 and 30 seconds'}), 400
        
        # Record and identify
        match_result = shazam.identify_from_microphone(duration=duration)
        
        if match_result:
            result = {
                'success': True,
                'match': {
                    'title': match_result.title,
                    'artist': match_result.artist,
                    'album': match_result.album,
                    'confidence': round(match_result.confidence, 3),
                    'matching_hashes': match_result.matching_hashes,
                    'alignment_strength': round(match_result.alignment_strength, 3)
                }
            }
        else:
            result = {
                'success': False,
                'message': 'No match found'
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Microphone identification failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/songs', methods=['GET'])
def list_songs():
    """
    List songs in the database.
    
    Query parameters:
        - limit: Maximum number of songs (default: 50)
        - offset: Number of songs to skip (default: 0)
        - search: Search query for title/artist
        
    Returns:
        - JSON with list of songs
    """
    try:
        limit = min(int(request.args.get('limit', 50)), 1000)
        offset = int(request.args.get('offset', 0))
        search_query = request.args.get('search', '').strip()
        
        if search_query:
            songs = shazam.search_songs(search_query, limit=limit)
        else:
            songs = shazam.database.list_songs(limit=limit, offset=offset)
        
        return jsonify({
            'songs': songs,
            'count': len(songs),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Failed to list songs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/songs/add', methods=['POST'])
def add_song():
    """
    Add a song to the database.
    
    Expects:
        - audio file in request.files['audio']
        - title in form data
        - artist in form data
        - album in form data (optional)
        
    Returns:
        - JSON with success status and song ID
    """
    try:
        # Check required fields
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        title = request.form.get('title', '').strip()
        artist = request.form.get('artist', '').strip()
        album = request.form.get('album', '').strip() or None
        
        if not title or not artist:
            return jsonify({'error': 'Title and artist are required'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            audio_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Add song to database
            song_id = shazam.add_song_to_database(
                audio_file=temp_path,
                title=title,
                artist=artist,
                album=album
            )
            
            if song_id:
                return jsonify({
                    'success': True,
                    'song_id': song_id,
                    'message': f"Added '{title}' by {artist}"
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to process audio file'
                }), 500
                
        finally:
            # Clean up temporary file
            os.unlink(temp_path)
            
    except Exception as e:
        logger.error(f"Failed to add song: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Get database and system statistics.
    
    Returns:
        - JSON with system statistics
    """
    try:
        stats = shazam.get_system_info()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/songs/<int:song_id>', methods=['GET'])
def get_song(song_id):
    """
    Get song details by ID.
    
    Args:
        song_id: Song ID
        
    Returns:
        - JSON with song details
    """
    try:
        song = shazam.database.get_song_metadata(song_id)
        
        if song:
            return jsonify(song)
        else:
            return jsonify({'error': 'Song not found'}), 404
            
    except Exception as e:
        logger.error(f"Failed to get song {song_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/songs/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    """
    Delete a song from the database.
    
    Args:
        song_id: Song ID
        
    Returns:
        - JSON with success status
    """
    try:
        success = shazam.database.remove_song(song_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Song {song_id} deleted'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Song not found or deletion failed'
            }), 404
            
    except Exception as e:
        logger.error(f"Failed to delete song {song_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(413)
def file_too_large(error):
    """Handle file size limit exceeded."""
    return jsonify({'error': 'File too large (max 50MB)'}), 413


@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


def create_app() -> Flask:
    """Create and configure Flask app."""
    return app


def run_api_server(host: str = API_HOST, port: int = API_PORT, debug: bool = API_DEBUG):
    """
    Run the API server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    logger.info(f"Starting Shazam API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the server
    run_api_server()
