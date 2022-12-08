
async function printFileUploadModalBody(text){
    let textbox = document.getElementById("fileUploadModalBodyText");
    textbox.value += text;
}

async function uploadFileToVolatile(files) {
    console.log(files);
    let textbox = document.getElementById("fileUploadModalBodyText");
    let fb = FILEBROWSER_LOOKUP['fileBrowserTable'];
    let fs = fb.fileSystems['browserfs'];
    let uploadedPaths = [];
    for (let file of files) {
        textbox.value += 'Uploading "' + file.name + '" to /browserfs/volatile/'+file.name+' ...';
        try{
            let data = await new Response(file).arrayBuffer();
            await fs.createFile('/volatile/' + file.name, data, false);
            textbox.value += 'Done!\r\n';
            uploadedPaths.push('/volatile/' + file.name);
        }
        catch(e){
            textbox.value += 'Error! Reason: '+ e + '\r\n';
        }
        
    }
    let start = new Date().toLocaleString();
    console.log("Start: " + start);
    textbox.value += '\r\nProcessing files...\r\n';
    for (let filepath of uploadedPaths) {
        textbox.value += 'Processing '+ filepath +'\r\n';
        await localFileCreated(filepath, null, printFileUploadModalBody);
    }
    textbox.value += 'Done processing all files!\r\n';
    let end = new Date().toLocaleString();
    console.log("End: " + end);
    
}

async function showFileUploadModal(files) {
	$(`<div class="modal fade fileUploadModalClass" id="fileUploadModal" tabindex="-1" role="dialog" aria-hidden="true" data-bs-backdrop="static">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <!-- Modal Header -->
                    <div class="modal-header">
                        <h4 class="modal-title">Info</h4>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" id="showFileBrowserInfoModalOKButton"></button>
                    </div>
        
                    <div class="modal-body">
                        <textarea class="consoleoutputfield" readonly id="fileUploadModalBodyText" rows=10 placeholder=""></textarea>
                        
                    </div>
                    
                    <!-- End modal body div -->
                </div>
                <!-- Modal Footer -->
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal" onclick="destroyFileUploadModal()">K.</button>
                    </div><!-- End Modal Footer -->
                <!-- End modal content div -->
            </div>
            <!-- End modal dialog div -->
        </div>
        <!-- End modal div -->`).appendTo("body").finish();
    
    $('#fileUploadModal').modal('show');
    await uploadFileToVolatile(files);
    await asyncTimeoutMs(3000);
    destroyFileUploadModal();
    
}

function destroyFileUploadModal(){
    $('#fileUploadModal').modal('hide');
    removeClass('fileUploadModalClass');
    
}