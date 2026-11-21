"""Small native setup window. Writes overrides, never touches game files."""
import json
import os
import sys
from pathlib import Path
from cloud import write, read

FILES = {'botw':'botw','oot':'oot','bloodborne':'bbport','arceus':'arceus','odyssey':'odyssey','pokopia':'pokopia'}

def save_configuration(root, data, game, selected, title_id=''):
    manifest = json.loads((root/'resources'/f'{FILES[game]}-adapter.json').read_text())
    path = Path(selected).expanduser().resolve(strict=True)
    if game == 'oot':
        if os.name == 'nt': raise ValueError('Select Live mode and choose bin/longshot.exe.')
        manifest['socket'] = str(path)
    elif game == 'bloodborne':
        import re
        if not path.is_dir(): raise ValueError('Select the BBPort user directory.')
        if not re.fullmatch(r'CUSA\d{5}', title_id): raise ValueError('Enter the CUSA title ID, for example CUSA00900.')
        manifest.update(root=str(path),titleId=title_id)
    else:
        if not path.is_file(): raise ValueError('Select a save file, not a directory.')
        manifest.update(root=str(path.parent),glob=path.name)
        # Explicitly choosing saves must work without any live launch wrapper.
        if game == 'pokopia': manifest.update(liveOnly=False)
    write(data/'adapters'/f'{FILES[game]}-adapter.json', manifest)

def configure(root, data):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    catalog = json.loads((root/'resources/catalog.json').read_text())
    app = tk.Tk(); app.title('Custom Steam Achievements — Game setup'); app.geometry('720x430')
    frame = ttk.Frame(app,padding=20); frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Select your game and its progress file.').pack(anchor='w')
    choices = list(FILES); names = [catalog[g]['name'] for g in choices]
    game = ttk.Combobox(frame,values=names,state='readonly'); game.current(0); game.pack(fill='x',pady=10)
    live=tk.BooleanVar(value=os.name=='nt')
    if os.name=='nt':ttk.Checkbutton(frame,text='Live tracking for Ocarina / Pokopia (no save needed)',variable=live).pack(anchor='w',pady=4)
    selected = tk.StringVar(); ttk.Entry(frame,textvariable=selected).pack(fill='x')
    def browse():
        value = filedialog.askdirectory() if choices[game.current()] == 'bloodborne' else filedialog.askopenfilename()
        if value: selected.set(value)
    ttk.Button(frame,text='Choose game .exe / save file / BBPort directory',command=browse).pack(anchor='w',pady=6)
    ttk.Label(frame,text='BOTW: game_data.sav · Arceus: main · Odyssey: File1.bin\nPokopia: CMNDAT.BIN · Ocarina: Longshot control socket').pack(anchor='w')
    main=tk.StringVar()
    if os.name=='nt':
        ttk.Label(frame,text='Pokopia Live: actual exefs/main file for game version 2.0.1').pack(anchor='w',pady=(8,0))
        ttk.Entry(frame,textvariable=main).pack(fill='x')
        def browse_main():
            value=filedialog.askopenfilename(title='Select Pokopia exefs/main')
            if value:main.set(value)
        ttk.Button(frame,text='Choose exefs/main',command=browse_main).pack(anchor='w')
    row=ttk.Frame(frame);row.pack(fill='x',pady=8)
    ttk.Label(row,text='Bloodborne title ID (only for BBPort): ').pack(side='left')
    title=tk.StringVar();ttk.Entry(row,textvariable=title,width=15).pack(side='left')
    def save():
        try:
            chosen=choices[game.current()]
            if os.name=='nt' and live.get() and chosen in ('oot','pokopia'):
                from windows_setup import configure_live,create_longshot_shortcut
                configure_live(root,data,chosen,selected.get(),main.get())
                if chosen=='oot':
                    link=create_longshot_shortcut(data)
                    messagebox.showinfo('Longshot Live configured',f'Launch using this shortcut:\n{link}\n\nFor your existing Steam shortcut, set Target to {sys.executable} and Launch Options to --launch-longshot. This enables the local control bridge.')
                else:messagebox.showinfo('Pokopia Live configured','Start the configured Recompia game normally. The tracker detects pkp.exe and reads live progress; no save or mod is needed. Open the game library page in Steam once for notifications.')
                return
            save_configuration(root,data,chosen,selected.get(),title.get().strip())
            messagebox.showinfo('Saved','Settings saved. Open this game in your Steam library once to connect notifications. The tracker reloads settings automatically.')
        except Exception as error: messagebox.showerror('Could not save',str(error))
    ttk.Button(frame,text='Save settings',command=save).pack(anchor='e')
    app.mainloop()
