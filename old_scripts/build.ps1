param([string] $gitRepoName,[string] $BuildType,[string] $eventName,[string] $commit)

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

if (($BuildType -eq '') -or ($gitRepoName -eq '') -or ($eventName -eq '') -or ($commit -eq ''))
    {
        Write-Host -ForegroundColor Red 'Missing parameters'
        exit 1
    }
$buildroot = 'C:\Linc-GithubWorkflows\AppBuilds\'
$workPath = 'C:\actions-runner\_work\' + $gitRepoName + '\' + $gitRepoName
$outpath = 'C:\actions-runner\_work\' + $gitRepoName + '\' + $gitRepoName
$symbolslocation = 'C:\actions-runner\_work\' + $gitRepoName + '\symbols'
# get app.json file of project
$appjsonfilepath = $workpath + '\app.json'

# substitute and get app.json for specific build versions
if ($BuildType -eq 'bc17')
    {
        $appjsonfilepath_bc17 = $workpath + '\bc17_app.json'
        if (Test-Path $appjsonfilepath_bc17)
            {
                Remove-Item $appjsonfilepath -force | Out-Null
                Rename-Item $appjsonfilepath_bc17 -NewName 'app.json' -force | Out-Null
            }
    }

if ($BuildType -eq 'bc18')
    {
        $appjsonfilepath_bc18 = $workpath + '\bc18_app.json'
        if (Test-Path $appjsonfilepath_bc18)
            {
                Remove-Item $appjsonfilepath -force | Out-Null
                Rename-Item $appjsonfilepath_bc18 -NewName 'app.json' -force | Out-Null
            }
    }

if ($BuildType -eq 'bc19')
    {
        $appjsonfilepath_bc19 = $workpath + '\bc19_app.json'
        if (Test-Path $appjsonfilepath_bc19)
            {
                Remove-Item $appjsonfilepath -force | Out-Null
                Rename-Item $appjsonfilepath_bc19 -NewName 'app.json' -force | Out-Null
            }
    }

    if ($BuildType -eq 'bc22')
    {
        $appjsonfilepath_bc22 = $workpath + '\bc22_app.json'
        if (Test-Path $appjsonfilepath_bc22)
            {
                Remove-Item $appjsonfilepath -force | Out-Null
                Rename-Item $appjsonfilepath_bc22 -NewName 'app.json' -force | Out-Null
            }
    }

if ($BuildType -eq 'bccloud')
    {
        $appjsonfilepath_cloud = $workpath + '\cloud_app.json'
        if (Test-Path $appjsonfilepath_cloud)
            {
                Remove-Item $appjsonfilepath -force | Out-Null
                Rename-Item $appjsonfilepath_cloud -NewName 'app.json' -force | Out-Null
            }
    }

# read app.json file into variables for later use
$appfile = Get-Content $appjsonfilepath | ConvertFrom-Json
$app_version = New-Object System.Version($appfile.version.ToString())
$app_platform = $appfile.platform
$app_dependencies = $appfile.dependencies
$appDestName = $appfile.name.Replace(" ","-").Replace("-","")

# construct new version for resulting build app file
$outversion_major = [System.Version]::Parse($app_platform).Major.ToString()
$outversion_minor = (Get-Date).ToString("yy")
$outversion_build = (New-TimeSpan -Start ([datetime]"01/01/2020") -End ($(Get-Date))).Days.ToString()
$outversion_revision = [math]::Truncate(($(Get-Date).TimeOfDay).TotalMinutes).ToString()

# only use the constructed version for production build, otherwise use 0.0.0.0 - for develop, use 99 as major
if (($eventname -eq 'push') -and (($BuildType -eq 'refs/heads/master') -or ($BuildType -like 'bc*')))
    {$outversion = New-Object System.Version($outversion_major,$outversion_minor,$outversion_build,$outversion_revision)}
elseif (($eventname -eq 'deploy') -and ($BuildType -eq 'develop'))
    {
    $outversion_major = '99'
    $outversion = New-Object System.Version($outversion_major,$outversion_minor,$outversion_build,$outversion_revision)
    }
else
    {$outversion = New-Object System.Version(0,0,0,0)}

# update local app.json with newly constructed version for build process
$appfile.version = $outversion.ToString()

# set showmycode to false irrespective of app.json setting
if ($gitRepoName.Contains("Customer"))
{
    if ($BuildType -ne 'develop')
        {if ($appfile.PSobject.Properties.Name.Contains("showMyCode"))
            {$appfile.showMyCode = $false}
        }
}

# store modified app.json file
$appfile | ConvertTo-Json | Set-Content $appjsonfilepath

# construct output app filename
$outfile = $appfile.name.Replace(' ','').Replace('-','') + '_' + $outversion + '_' + $commit.substring(0,7) + '.app'

# set variables for alcompiler
$ruleset = $workpath + '\LincRuleSet.json'
$target = $appfile.target
$application = $appfile.application
$application_major = [System.Version]::Parse($application).Major.ToString()
$runtime = $appfile.runtime
$generatereportlayout = '-'
$assemblyprobingpaths = 'C:\Windows\Microsoft.NET\Framework\v4.0.30319'
$buildDestination = $buildroot + $appDestName + '\'

if ($BuildType -eq 'bc17')
    {$buildDestination = $buildroot + $appDestName + '\bc17\'}
if ($BuildType -eq 'bc18')
    {$buildDestination = $buildroot + $appDestName + '\bc18\'}    
if ($BuildType -eq 'bc19')
    {$buildDestination = $buildroot + $appDestName + '\bc19\'}    
if ($BuildType -eq 'bc22')
    {$buildDestination = $buildroot + $appDestName + '\bc22\'}    
if ($BuildType -eq 'bccloud')
    {$buildDestination = $buildroot + $appDestName + '\bccloud\'}
if ($BuildType -eq 'develop')
    {$buildDestination = $buildroot + $appDestName + '\'}
$errorLog = $buildDestination + 'errorLog.json'

# create the destination directory if it does not exist
if (!(Test-Path -Path $buildDestination ))
    {New-Item -ItemType directory -Path $buildDestination | Out-Null}

# clear up previous errorlog if exists
$appPathToDelete = $buildDestination + 'errorLog.json'
if (Test-Path $appPathToDelete)
    {Remove-Item $appPathToDelete -force | Out-Null}

# delete appropriate permission file, based on runtime (if any of the above efforts failed)
if ([decimal]$runtime -ge 8.1)
    {
        $searchstring = $workpath + '\extensionsPermissionSet.xml'
        $permissionobject = Get-ChildItem $searchstring -ErrorAction Ignore | Select-Object -First 1
        if ($permissionobject -ne $null)
        {
            if (Test-Path $permissionobject)
                {Remove-Item $permissionobject -force | Out-Null} 
        }
    }
else
    {
        $searchstring = $workpath + '\PermissionSet*.al'
        $permissionobject = Get-ChildItem $searchstring -ErrorAction Ignore | Select-Object -First 1
        if ($permissionobject -ne $null)
            {
                if (Test-Path $permissionobject)
                    {Remove-Item $permissionobject -force | Out-Null} 
            }
    }

# collect the appropriate symbols together
if (Test-Path $symbolslocation)
    {Remove-Item -Path $symbolslocation -Recurse -ErrorAction Ignore | Out-Null}
New-Item -ItemType "directory" -Path $symbolslocation -ErrorAction Ignore | Out-Null
# non microsoft app dependencies
foreach ($d in $app_dependencies)
    {
        $symbolsourcepath = $buildroot + $d.name.Replace(" ","-").Replace("-","")
        if ($target -eq 'OnPrem')
        {
            if (($d.name -eq 'Linc General Business Extensions'))
                {$symbolsourcepath = $symbolsourcepath + '\bc22'}        
        }
        else {
            if ($BuildType -eq 'bc17')
            {$symbolsourcepath = $symbolsourcepath + '\bc17'}
            if ($BuildType -eq 'bc18')
            {$symbolsourcepath = $symbolsourcepath + '\bc18'}
            if ($BuildType -eq 'bc19')
            {$symbolsourcepath = $symbolsourcepath + '\bc19'}
            if ($BuildType -eq 'bc22')
            {$symbolsourcepath = $symbolsourcepath + '\bc22'}
            if ($BuildType -eq 'bccloud')
            {$symbolsourcepath = $symbolsourcepath + '\bccloud'}
        }
        if (-not (Test-Path $symbolsourcepath))
            {$symbolsourcepath = $buildroot + $d.name.Replace(" ","-").Replace("-","")}
        $searchstring = $symbolsourcepath + '\*.app'
        $appobject = Get-ChildItem $searchstring -ErrorAction Ignore | Select-Object -First 1
        if ($appobject -ne $null)
        {
            if (Test-Path $appobject)
                {
                    Copy-Item -Path $appobject.FullName -Destination $symbolslocation -force | Out-Null
                } 
        }
    }
# microsoft symbols
switch ($application_major)
    {
        '14'{$symbolsourcepath = $buildroot + '\Microsoft\BC14\*'}
        '16'{$symbolsourcepath = $buildroot + '\Microsoft\BC16\*'}
        '17'{$symbolsourcepath = $buildroot + '\Microsoft\BC17\*'}
        '18'{$symbolsourcepath = $buildroot + '\Microsoft\BC18\*'}
        '19'{$symbolsourcepath = $buildroot + '\Microsoft\BC19\*'}
        '20'{$symbolsourcepath = $buildroot + '\Microsoft\BC20\*'}
        '21'{$symbolsourcepath = $buildroot + '\Microsoft\BC21\*'}
        '22'{$symbolsourcepath = $buildroot + '\Microsoft\BC22\*'}
        '23'{$symbolsourcepath = $buildroot + '\Microsoft\BC23\*'}
        '24'{$symbolsourcepath = $buildroot + '\Microsoft\BC24\*'}
        '25'{$symbolsourcepath = $buildroot + '\Microsoft\BC25\*'}
        '26'{$symbolsourcepath = $buildroot + '\Microsoft\BC26\*'}
    }
Copy-Item -Path $symbolsourcepath -Destination $symbolslocation -force | Out-Null

# run the alcompiler
$searchstring = 'C:\users\Administrator\.vscode\extensions\ms-dynamics-smb.al-*'
$ALExecutable = Get-ChildItem $searchstring -ErrorAction Ignore | Select-Object -First 1
$ALpath = $ALExecutable.FullName
    
& $ALpath\bin\win32\alc.exe /packagecachepath:$symbolslocation /assemblyprobingpaths:$assemblyprobingpaths /project:$workPath /out:$outfile /target:$target /loglevel:Normal /errorlog:$errorLog /generatereportlayout:$generatereportlayout /ruleset:$ruleset

if ($LASTEXITCODE -eq 0) # the alcompile did not cause an error
{
    # if production build, sign the app file and move build artifact to destination folder, otherwise destroy artifact
    if (($eventname -eq 'push') -and (($BuildType -contains 'refs/heads/master') -or ($BuildType -like 'bc*')))
        {
            $appPathToArchive = $buildDestination + '*.app'
            $archivedestination = $buildDestination + '\old_builds\'
            # create  archive folder if not exists
            if (!(Test-Path -Path $archivedestination))
                {New-Item -ItemType directory -Path $archivedestination | Out-Null}
            if (Test-Path $appPathToArchive) 
                {Move-Item -Path $appPathToArchive $archivedestination -force | Out-Null}
            $source = $outpath + '\*.app'
            # sign the app file
            $AZ_KEY_VAULT_URI="https://linccodesigning.vault.azure.net/"
            $AZ_KEY_VAULT_CERTIFICATE_NAME="DigiCertCodeSigning"
            $AZ_KEY_VAULT_APPLICATION_ID="67d99351-bc7a-4730-a061-f435aa4bb399"
            $AZ_KEY_VAULT_APPLICATION_SECRET="iiw8Q~bXSpgFyoWSEJC.rzWAL7.BYU0GfS3X.agz"
            $AZ_KEY_VAULT_TENANT_ID="9d9672cd-de63-40b4-923d-3651563114a2"
            & azuresigntool @("sign","-kvu","$AZ_KEY_VAULT_URI","-kvc","$AZ_KEY_VAULT_CERTIFICATE_NAME","-kvi","$AZ_KEY_VAULT_APPLICATION_ID","-kvs","$AZ_KEY_VAULT_APPLICATION_SECRET","-kvt","$AZ_KEY_VAULT_TENANT_ID","-tr","http://timestamp.digicert.com","-v","$outfile")
            # move build artifact to destination
            $destination = $buildDestination
            Copy-Item -Path $source -Destination $destination | Out-Null
            Write-Host -ForegroundColor Green 'Successful Build:' $appfile.name 'version' $outversion 'at commit' $commit.Substring(0,7)
            $build_number = $outversion.ToString() + "_" + $commit.Substring(0,7)
            echo "build_number=$build_number" | Out-File -FilePath $Env:GITHUB_ENV -Encoding utf8 -Append
        }
    elseif (($eventname -eq 'deploy') -and ($BuildType -eq 'develop'))
        {
            $source = $workPath + '\*.app'
            $developdestination = $buildDestination + '\develop\'
            $appPathToDelete = $buildDestination + '\develop\' + '*.app'
            Remove-Item $appPathToDelete -force | Out-Null
            $destination = $developdestination
            Move-Item -Path $source -Destination $destination | Out-Null
            Write-Host -ForegroundColor Green 'Successful Build of Develop:' $appfile.name
        }
    else
        {
            $source = $workPath + '\*.app'
            Remove-Item $source -force | Out-Null
            Write-Host -ForegroundColor Green 'Successful Compile Test:' $appfile.name 'at commit' $commit.Substring(0,7)
        }
}

# reset local app.json to before build process (whether build was successful or not)
$appfile.version = $app_version.ToString()
$appfile | ConvertTo-Json | Set-Content $appjsonfilepath 
