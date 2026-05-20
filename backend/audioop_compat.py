"""
Compatibility shim for Python 3.14+ which removed the audioop module.
This provides minimal mock implementations for pydub compatibility.
"""

import sys
from collections import namedtuple

# Create a mock audioop module if it doesn't exist
if 'audioop' not in sys.modules:
    class MockAudioop:
        """Mock audioop module for Python 3.14+ compatibility."""
        
        @staticmethod
        def add(cp1, cp2, n):
            """Mock add operation."""
            return b''
        
        @staticmethod
        def bias(cp, n, bias):
            """Mock bias operation."""
            return cp
        
        @staticmethod
        def cross(cp, n):
            """Mock cross operation."""
            return 0
        
        @staticmethod
        def mul(cp, n, factor):
            """Mock mul operation."""
            return cp
        
        @staticmethod
        def tomono(cp, n, lfac, rfac):
            """Mock tomono operation."""
            return cp
        
        @staticmethod
        def tostereo(cp, n, lfac, rfac):
            """Mock tostereo operation."""
            return cp
        
        @staticmethod
        def avg(cp, n):
            """Mock avg operation."""
            return 0
        
        @staticmethod
        def avgpp(cp, n):
            """Mock avgpp operation."""
            return 0
        
        @staticmethod
        def maxpp(cp, n):
            """Mock maxpp operation."""
            return 0
        
        @staticmethod
        def max(cp, n):
            """Mock max operation."""
            return 0
        
        @staticmethod
        def minmax(cp, n):
            """Mock minmax operation."""
            return (0, 0)
        
        @staticmethod
        def rms(cp, n):
            """Mock rms operation."""
            return 0
        
        @staticmethod
        def reverse(cp, n):
            """Mock reverse operation."""
            return cp[::-1]
        
        @staticmethod
        def lin2lin(cp, size, nchannels):
            """Mock lin2lin operation."""
            return cp
        
        @staticmethod
        def lin2alaw(cp, n):
            """Mock lin2alaw operation."""
            return cp
        
        @staticmethod
        def lin2ulaw(cp, n):
            """Mock lin2ulaw operation."""
            return cp
        
        @staticmethod
        def alaw2lin(cp, n):
            """Mock alaw2lin operation."""
            return cp
        
        @staticmethod
        def ulaw2lin(cp, n):
            """Mock ulaw2lin operation."""
            return cp
        
        @staticmethod
        def adpcm2lin(cp, n, state):
            """Mock adpcm2lin operation."""
            return cp, state
        
        @staticmethod
        def lin2adpcm(cp, n, state):
            """Mock lin2adpcm operation."""
            return cp, state
    
    sys.modules['audioop'] = MockAudioop()

# Also handle pyaudioop if needed
if 'pyaudioop' not in sys.modules:
    sys.modules['pyaudioop'] = sys.modules.get('audioop')
