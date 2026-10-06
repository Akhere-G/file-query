import { ThemeToggle } from "@/components/settings/ThemeToggle";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function SettingsPage() {
  return (
    <div className="container mx-auto py-10 px-4 md:px-8 max-w-4xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your account settings and preferences.
        </p>
      </div>
      
      <Separator />
      
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>
              Customize how FileQuery looks on your device.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <h3 className="text-sm font-medium leading-none">Theme Preference</h3>
                <p className="text-sm text-muted-foreground">
                  Select your preferred color theme.
                </p>
              </div>
              <ThemeToggle />
            </div>
          </CardContent>
        </Card>
        
        {/* Additional settings sections can be added here in the future */}
      </div>
    </div>
  );
}
