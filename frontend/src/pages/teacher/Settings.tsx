import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

type SettingsData = Awaited<ReturnType<typeof api.settings.get>>["settings"];

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [readiness, setReadiness] = useState({ openai: false, bfl: false });
  const [localData, setLocalData] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.settings.get().then((response) => {
      setSettings(response.settings);
      setReadiness(response.provider_readiness);
      setLocalData(response.local_data);
    }).catch(() => setMessage("Settings could not be loaded."));
  }, []);

  if (!settings) return <p role="status">Loading settings...</p>;

  const save = async () => {
    try {
      await api.settings.update(settings);
      setMessage("Settings saved.");
    } catch {
      setMessage("Settings could not be saved. Your choices are still shown.");
    }
  };

  const reset = async () => {
    try {
      await api.settings.reset();
      setMessage("Local application data reset.");
    } catch {
      setMessage("Reset is incomplete. Retry to finish local file cleanup.");
    }
  };

  return <main className="container mx-auto max-w-3xl space-y-6 px-4 py-8">
    <h1 className="text-4xl font-bold">Settings</h1>
    <Card><CardContent className="space-y-5 pt-6">
      <fieldset className="space-y-2">
        <legend className="font-semibold">Story length</legend>
        {[12, 20].map((count) => <label key={count} className="flex min-h-11 items-center gap-2">
          <input type="radio" name="story-length" checked={settings.story_length === count}
            aria-label={count === 20 ? "20 panels (Full comic)" : "12 panels"}
            onChange={() => setSettings({ ...settings, story_length: count as 12 | 20 })} />
          {count === 20 ? "20 panels — Full comic" : "12 panels — Standard"}
        </label>)}
      </fieldset>
      <label className="block">Default classroom style
        <select className="mt-1 min-h-11 w-full rounded-md border bg-background px-3" value={settings.default_design_style}
          onChange={(event) => setSettings({ ...settings, default_design_style: event.target.value as SettingsData["default_design_style"] })}>
          <option value="comic">Comic</option><option value="manga">Manga</option><option value="cartoon">Cartoon</option>
        </select>
      </label>
      <div className="space-y-2"><p className="font-semibold">Provider models</p>
        <label className="block">OpenAI model
          <select className="mt-1 min-h-11 w-full rounded-md border bg-background px-3" value={settings.openai_model}
            onChange={(event) => setSettings({ ...settings, openai_model: event.target.value as SettingsData["openai_model"] })}>
            <option value="gpt-5.6-terra">Terra — balanced cost and quality</option>
            <option value="gpt-5.6-sol">Sol — highest quality</option>
            <option value="gpt-5.6-luna">Luna — fastest and lowest cost</option>
          </select>
        </label>
        <label className="block">BFL model
          <select className="mt-1 min-h-11 w-full rounded-md border bg-background px-3" value={settings.bfl_model}
            onChange={(event) => setSettings({ ...settings, bfl_model: event.target.value as SettingsData["bfl_model"] })}>
            <option value="flux-2-pro">Pro — default continuity and cost balance</option>
            <option value="flux-2-flex">Flex — optional, higher-cost typography choice</option>
          </select>
        </label>
        <p>OpenAI: {readiness.openai ? "ready" : "key not configured"}</p><p>BFL: {settings.bfl_model} ({readiness.bfl ? "ready" : "key not configured"})</p></div>
      <label className="flex min-h-11 items-center gap-3">
        <Checkbox checked={settings.automatic_panel_review} onCheckedChange={(checked) => setSettings({ ...settings, automatic_panel_review: checked === true })} />
        Automatically review generated panels
      </label>
      <p className="text-sm text-muted-foreground">Off by default. Each retry can add one OpenAI vision review and another BFL image generation, increasing duration and BYOK spend. This applies only to new generations.</p>
      <label className="block">Panel review attempts
        <select className="mt-1 min-h-11 w-full rounded-md border bg-background px-3" value={settings.panel_review_attempt_cap}
          onChange={(event) => setSettings({ ...settings, panel_review_attempt_cap: Number(event.target.value) as 1 | 2 | 3 })}>
          <option value="1">1</option><option value="2">2</option><option value="3">3</option>
        </select>
      </label>
      <Button onClick={save}>Save settings</Button>
    </CardContent></Card>
    <Card><CardContent className="space-y-4 pt-6"><h2 className="text-xl font-semibold">Local data</h2><p>{localData}</p>
      <AlertDialog><AlertDialogTrigger asChild><Button variant="destructive">Reset local data</Button></AlertDialogTrigger>
        <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Reset all local data?</AlertDialogTitle>
          <AlertDialogDescription>This deletes every classroom, student profile, story, and managed file on this device.</AlertDialogDescription>
        </AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={reset}>Confirm reset</AlertDialogAction></AlertDialogFooter></AlertDialogContent>
      </AlertDialog>
    </CardContent></Card>
    {message && <p role="status">{message}</p>}
  </main>;
}
