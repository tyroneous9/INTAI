import logging
import threading
import time
import os
import datetime
import cv2
import dxcam


class ScreenManager:
    """
    DXGI-based screen capture manager using `dxcam`.
    Does NOT lock frame updates — latest frame may be corrupted if read during update.
    """

    def __init__(self, stop_event):
        """
        Initialize the ScreenManager.

        Args:
            stop_event (threading.Event): Event the caller sets to request its managed thread to stop
        """
        self.stop_event = stop_event
        self._dxcam = None
        self._manager_thread = None
        self._latest_frame = None
        try:
            
            self._dxcam = dxcam.create(output_color="BGR")
        except Exception:
            raise RuntimeError("dxcam backend not available — install dxcam for DXGI capture")


    def start_capture_thread(self, fps=30):
        """
        Starts a background thread to constantly update the latest frame at the specified FPS.
        Args:
            fps (int): Frames per second to capture.
        """
        if self._manager_thread and self._manager_thread.is_alive():
            logging.error("Capture thread is already running.")
            raise RuntimeError("Capture thread is already running.")

        def _loop():
            period = 1.0 / max(1, int(fps))
            while not self.stop_event.is_set():
                try:
                    f = self._dxcam.grab()
                    self._latest_frame = f
                except Exception:
                    logging.exception("dxcam capture error")
                time.sleep(period)

        self._manager_thread = threading.Thread(target=_loop, daemon=True)
        self._manager_thread.start()
        while self._latest_frame is None:
            time.sleep(0.1)


    def stop_capture_thread(self, timeout=60):
        """
        Stops the background capture thread.
        Args:
            timeout (int): Time in seconds to wait for the thread to stop.
        """
        if self._manager_thread:
            try:
                self.stop_event.set()
                self._manager_thread.join(timeout=timeout)
            finally:
                if self._manager_thread.is_alive():
                    logging.error("Capture thread failed to exit within the given timeout.")
                    raise RuntimeError("Capture thread failed to exit within the given timeout.")
                else:
                    self._manager_thread = None
                    logging.info("Capture thread has exited.")
        else:
            logging.error("Capture thread is not running, failed to close")

    def get_latest_frame(self):
        """
        Returns the latest captured frame.
        """
        return self._latest_frame
    

    def get_screenshot(self):
        """
        Captures and returns a single screenshot frame.
        """
        try:
            f = self._dxcam.grab()
            return f
        except Exception:
            logging.exception("dxcam capture error")
            return None


    def save_screenshot(self, file_name="screenshot"):
        """
        Capture a single frame (via `get_screenshot`) and save it to the `temp/`
        directory as a PNG with a timestamped filename.

        Returns:
            str | None: full path to written file on success, else None.
        """
        frame = self.get_screenshot()
        if frame is None:
            logging.error("No frame captured; not saving screenshot.")
            return None

        out_dir = os.path.join("temp")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            logging.exception("Failed to create temp directory")
            return None

        filename = f"{file_name}_.png"
        out_path = os.path.join(out_dir, filename)
        try:
            # frame is BGR; write directly
            ok = cv2.imwrite(out_path, frame)
            if not ok:
                logging.error("cv2.imwrite failed for %s", out_path)
                return None
            return out_path
        except Exception:
            logging.exception("Failed to write screenshot to disk")
            return None