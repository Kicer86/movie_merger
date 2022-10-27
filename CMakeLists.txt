
project(VOF LANGUAGES)

cmake_minimum_required(VERSION 3.20)

find_program(ffmpeg ffmpeg REQUIRED)
find_program(avidemux avidemux3_cli REQUIRED)

set(testVideos)
set(horizontalVideos "Atoms - 8579.mp4" "Frog - 113403.mp4" "Grass - 66810.mp4" "sea-waves-crashing-on-beach-shore-4793288.mp4" "Woman - 58142.mp4")
set(resolutions 2160;1080;720;360)

# convert all horizontal movies into 4 different resolutions
foreach(resolution ${resolutions})

    set(segments)
    foreach(videoFile ${horizontalVideos})
        get_filename_component(videoName ${videoFile} NAME_WE)
        set(outputFileName "${videoName}-${resolution}p.mp4")
        add_custom_command(
            OUTPUT test-videos/${outputFileName}
            COMMAND ${ffmpeg} -y -i ${CMAKE_CURRENT_SOURCE_DIR}/VOF-media/${videoFile} -filter:v scale=-1:${resolution} test-videos/${outputFileName}
        )
        list(APPEND segments test-videos/${outputFileName})
        set_source_files_properties(test-videos/${outputFileName} PROPERTIES GENERATED TRUE)
    endforeach()

    # combine horizontal files into movies combining all of them (per resolution)
    set(inputFiles)
    set(first TRUE)
    foreach(videoFile ${segments})
        if(first)
            set(inputFiles ${inputFiles} --load ${videoFile})
        else()
            set(inputFiles ${inputFiles} --append ${videoFile})
        endif()
        set(first FALSE)
    endforeach()

    set(outputFileName movie-${resolution}p.mp4)
    add_custom_command(
            OUTPUT test-videos/${outputFileName}
            COMMAND ${avidemux} ${inputFiles} --video-codec Copy --save test-videos/${outputFileName}
            DEPENDS ${segments}
        )
    list(APPEND testVideos test-videos/${outputFileName})

endforeach()


add_custom_target(makeVideos
    DEPENDS ${testVideos}
)
