"""GC2 Connect - NiceGUI Application."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from nicegui import ui, app

from gc2_connect.models import GC2ShotData, GSProResponse
from gc2_connect.gc2.usb_reader import GC2USBReader, MockGC2Reader
from gc2_connect.gspro.client import GSProClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GC2ConnectApp:
    """Main application class."""
    
    def __init__(self):
        # State
        self.gc2_reader: Optional[GC2USBReader | MockGC2Reader] = None
        self.gspro_client: Optional[GSProClient] = None
        self.shot_history: list[GC2ShotData] = []
        self.auto_send = True
        self.use_mock_gc2 = False
        
        # UI references
        self.gc2_status_label = None
        self.gspro_status_label = None
        self.shot_display = None
        self.history_list = None
        self.gspro_host_input = None
        self.gspro_port_input = None
        
        # Tasks
        self._gc2_task: Optional[asyncio.Task] = None
    
    def build_ui(self):
        """Build the NiceGUI interface."""
        ui.dark_mode().enable()
        
        with ui.header().classes('bg-blue-900'):
            ui.label('GC2 Connect').classes('text-2xl font-bold')
            ui.space()
            with ui.row().classes('items-center'):
                ui.label('Auto-send to GSPro:')
                ui.switch(value=True, on_change=lambda e: setattr(self, 'auto_send', e.value))
        
        with ui.row().classes('w-full gap-4 p-4'):
            # Left column - Connections
            with ui.column().classes('w-1/3'):
                self._build_gc2_panel()
                self._build_gspro_panel()
            
            # Center column - Current Shot
            with ui.column().classes('w-1/3'):
                self._build_shot_display()
            
            # Right column - Shot History
            with ui.column().classes('w-1/3'):
                self._build_history_panel()
    
    def _build_gc2_panel(self):
        """Build the GC2 connection panel."""
        with ui.card().classes('w-full'):
            ui.label('GC2 Launch Monitor').classes('text-lg font-bold')
            ui.separator()
            
            with ui.row().classes('items-center gap-2'):
                self.gc2_status_label = ui.label('Disconnected').classes('text-red-500')
                ui.badge('USB').classes('bg-gray-600')
            
            with ui.row().classes('gap-2 mt-4'):
                ui.button('Connect', on_click=self._connect_gc2).classes('bg-green-600')
                ui.button('Disconnect', on_click=self._disconnect_gc2).classes('bg-red-600')
            
            with ui.row().classes('items-center gap-2 mt-2'):
                ui.checkbox('Use Mock GC2', value=False, 
                           on_change=lambda e: setattr(self, 'use_mock_gc2', e.value))
                ui.button('Send Test Shot', on_click=self._send_test_shot).props('flat')
    
    def _build_gspro_panel(self):
        """Build the GSPro connection panel."""
        with ui.card().classes('w-full mt-4'):
            ui.label('GSPro Connection').classes('text-lg font-bold')
            ui.separator()
            
            with ui.row().classes('items-center gap-2'):
                self.gspro_status_label = ui.label('Disconnected').classes('text-red-500')
            
            with ui.column().classes('gap-2 mt-2'):
                self.gspro_host_input = ui.input(
                    label='GSPro IP Address',
                    value='192.168.1.100',
                    placeholder='e.g., 192.168.1.100'
                ).classes('w-full')
                
                self.gspro_port_input = ui.input(
                    label='Port',
                    value='921',
                    placeholder='921'
                ).classes('w-32')
            
            with ui.row().classes('gap-2 mt-4'):
                ui.button('Connect', on_click=self._connect_gspro).classes('bg-green-600')
                ui.button('Disconnect', on_click=self._disconnect_gspro).classes('bg-red-600')
    
    def _build_shot_display(self):
        """Build the current shot display panel."""
        with ui.card().classes('w-full h-full'):
            ui.label('Current Shot').classes('text-lg font-bold')
            ui.separator()
            
            self.shot_display = ui.column().classes('w-full')
            
            with self.shot_display:
                ui.label('No shot data yet').classes('text-gray-500 italic')
    
    def _build_history_panel(self):
        """Build the shot history panel."""
        with ui.card().classes('w-full h-full'):
            with ui.row().classes('items-center justify-between w-full'):
                ui.label('Shot History').classes('text-lg font-bold')
                ui.button('Clear', on_click=self._clear_history).props('flat size=sm')
            
            ui.separator()
            
            self.history_list = ui.column().classes('w-full max-h-96 overflow-y-auto')
    
    def _update_shot_display(self, shot: GC2ShotData):
        """Update the shot display with new data."""
        self.shot_display.clear()
        
        with self.shot_display:
            # Ball Data Section
            ui.label('Ball Data').classes('text-md font-semibold text-blue-400')
            
            with ui.grid(columns=2).classes('gap-2 w-full'):
                self._stat_card('Ball Speed', f'{shot.ball_speed:.1f}', 'mph')
                self._stat_card('Launch Angle', f'{shot.launch_angle:.1f}', '°')
                self._stat_card('H. Launch', f'{shot.horizontal_launch_angle:.1f}', '°')
                self._stat_card('Total Spin', f'{shot.total_spin:.0f}', 'RPM')
                self._stat_card('Back Spin', f'{shot.back_spin:.0f}', 'RPM')
                self._stat_card('Side Spin', f'{shot.side_spin:.0f}', 'RPM')
                self._stat_card('Spin Axis', f'{shot.spin_axis:.1f}', '°')
            
            # Club Data Section (if available)
            if shot.has_club_data:
                ui.separator().classes('my-2')
                ui.label('Club Data (HMT)').classes('text-md font-semibold text-green-400')
                
                with ui.grid(columns=2).classes('gap-2 w-full'):
                    if shot.club_speed:
                        self._stat_card('Club Speed', f'{shot.club_speed:.1f}', 'mph')
                    if shot.swing_path is not None:
                        self._stat_card('Path', f'{shot.swing_path:.1f}', '°')
                    if shot.face_to_target is not None:
                        self._stat_card('Face', f'{shot.face_to_target:.1f}', '°')
                    if shot.angle_of_attack is not None:
                        self._stat_card('Attack', f'{shot.angle_of_attack:.1f}', '°')
    
    def _stat_card(self, label: str, value: str, unit: str):
        """Create a stat display card."""
        with ui.column().classes('bg-gray-800 rounded p-2'):
            ui.label(label).classes('text-xs text-gray-400')
            with ui.row().classes('items-baseline'):
                ui.label(value).classes('text-xl font-bold')
                ui.label(unit).classes('text-sm text-gray-400 ml-1')
    
    def _add_to_history(self, shot: GC2ShotData):
        """Add a shot to the history list."""
        self.shot_history.insert(0, shot)
        
        # Keep only last 50 shots
        if len(self.shot_history) > 50:
            self.shot_history = self.shot_history[:50]
        
        self._refresh_history()
    
    def _refresh_history(self):
        """Refresh the history list display."""
        self.history_list.clear()
        
        with self.history_list:
            for shot in self.shot_history[:20]:
                with ui.row().classes('w-full bg-gray-800 rounded p-2 mb-1 items-center'):
                    ui.label(f'#{shot.shot_id}').classes('text-sm text-gray-400 w-12')
                    ui.label(f'{shot.ball_speed:.1f} mph').classes('text-sm font-bold w-20')
                    ui.label(f'{shot.launch_angle:.1f}°').classes('text-sm w-12')
                    ui.label(f'{shot.total_spin:.0f} rpm').classes('text-sm w-20')
                    ui.label(shot.timestamp.strftime('%H:%M:%S')).classes('text-xs text-gray-500')
    
    def _clear_history(self):
        """Clear the shot history."""
        self.shot_history.clear()
        self._refresh_history()
    
    async def _connect_gc2(self):
        """Connect to the GC2."""
        if self.use_mock_gc2:
            self.gc2_reader = MockGC2Reader()
        else:
            self.gc2_reader = GC2USBReader()
        
        self.gc2_reader.add_shot_callback(self._on_shot_received)
        
        if self.gc2_reader.connect():
            self.gc2_status_label.text = 'Connected'
            self.gc2_status_label.classes(remove='text-red-500', add='text-green-500')
            
            # Start read loop
            self._gc2_task = asyncio.create_task(self.gc2_reader.read_loop())
            ui.notify('GC2 Connected!', type='positive')
        else:
            self.gc2_status_label.text = 'Connection Failed'
            ui.notify('Failed to connect to GC2', type='negative')
    
    def _disconnect_gc2(self):
        """Disconnect from the GC2."""
        if self._gc2_task:
            self._gc2_task.cancel()
            self._gc2_task = None
        
        if self.gc2_reader:
            self.gc2_reader.disconnect()
            self.gc2_reader = None
        
        self.gc2_status_label.text = 'Disconnected'
        self.gc2_status_label.classes(remove='text-green-500', add='text-red-500')
        ui.notify('GC2 Disconnected', type='info')
    
    async def _connect_gspro(self):
        """Connect to GSPro."""
        host = self.gspro_host_input.value
        port = int(self.gspro_port_input.value)
        
        self.gspro_client = GSProClient(host=host, port=port)
        
        if await self.gspro_client.connect_async():
            self.gspro_status_label.text = f'Connected to {host}:{port}'
            self.gspro_status_label.classes(remove='text-red-500', add='text-green-500')
            ui.notify('GSPro Connected!', type='positive')
        else:
            self.gspro_status_label.text = 'Connection Failed'
            ui.notify('Failed to connect to GSPro', type='negative')
    
    def _disconnect_gspro(self):
        """Disconnect from GSPro."""
        if self.gspro_client:
            self.gspro_client.disconnect()
            self.gspro_client = None
        
        self.gspro_status_label.text = 'Disconnected'
        self.gspro_status_label.classes(remove='text-green-500', add='text-red-500')
        ui.notify('GSPro Disconnected', type='info')
    
    def _on_shot_received(self, shot: GC2ShotData):
        """Handle a new shot from the GC2."""
        logger.info(f"Shot received: #{shot.shot_id}")
        
        # Update UI (must be done in main thread)
        self._update_shot_display(shot)
        self._add_to_history(shot)
        
        # Send to GSPro if connected and auto-send enabled
        if self.auto_send and self.gspro_client and self.gspro_client.is_connected:
            response = self.gspro_client.send_shot(shot)
            if response and response.is_success:
                ui.notify(f'Shot #{shot.shot_id} sent to GSPro', type='positive')
            else:
                ui.notify('Failed to send shot to GSPro', type='warning')
    
    def _send_test_shot(self):
        """Send a test shot (mock mode only)."""
        if isinstance(self.gc2_reader, MockGC2Reader):
            self.gc2_reader.send_test_shot()
        else:
            ui.notify('Enable Mock GC2 mode to send test shots', type='info')


def create_app():
    """Create and configure the application."""
    gc2_app = GC2ConnectApp()
    gc2_app.build_ui()
    return gc2_app


@ui.page('/')
def main_page():
    """Main page."""
    create_app()


def main():
    """Entry point."""
    ui.run(
        title='GC2 Connect',
        port=8080,
        reload=False,
        show=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
