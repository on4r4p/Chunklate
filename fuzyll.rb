#!/usr/bin/env ruby

require "zlib"

abort "Usage: #{__FILE__} <input_file> <output_file>" if ARGV.size < 1

File.open(ARGV.shift, "rb") do |input|
    File.open(ARGV.shift, "wb") do |output|
        # read file into memory
        file = input.read()
        puts "[+] Read file of size #{file.length}"

        # correct header if necessary
        if file[4] != "\r"
            file.insert(4, "\r")
        end
        output.write(file[0..7])

        # find all chunks via text search of type (finding them via size may not work due to corrruption)
        offsets = []
        ["IHDR", "PLTE", "IDAT", "IEND", "sBIT", "pHYs", "tEXt"].each do |type|
            file.scan(type) do |match|
                offsets << (Regexp.last_match.offset(0)[0] - 4)
            end
        end
        offsets.sort!
        offsets << file.length

        # attempt to fix all broken chunks
        i = 0
        while i < (offsets.length - 1) do
            # get the chunk out of the file
            chunk = file[offsets[i]..(offsets[i+1]-1)]
            size = chunk[0..3].unpack("L>")[0]  # first 4 bytes are chunk's size
            type = chunk[4..7]  # next 4 bytes are chunk's type
            crc = chunk[-4..-1].unpack("L>")[0]  # last 4 bytes are chunk's CRC

            # only process incorrect chunks
            if Zlib.crc32(chunk[4..-5]) == crc  # CRC only checks type + data
                output.write(chunk)
                i += 1
            else
                # ensure we are actually missing bytes in the chunk
                missing = size - (chunk.length - 12)
                if missing == 0
                    puts "[!] Cannot fix broken #{chunk[4..7]} chunk @ 0x#{offsets[i].to_s(16)}: No missing bytes!"
                    output.write(chunk)
                    i += 1
                    next
                elsif missing < 0
                    puts "[!] Cannot fix broken #{chunk[4..7]} chunk @ 0x#{offsets[i].to_s(16)}: Incorrect size!"
                    output.write(chunk)
                    i += 1
                    next
                else
                    puts "[*] #{chunk[4..7]} @ 0x#{offsets[i].to_s(16)} is missing #{missing} bytes"
                end

                # check all combinations of added bytes to see if we can fix the chunk
                linefeeds = []
                chunk.scan("\n") do |lf|
                    linefeeds << Regexp.last_match.offset(0)[0]
                end
                possibilities = linefeeds.combination(missing)
                if possibilities.count <= 0
                    puts "[!] Cannot fix broken #{chunk [4..7]} chunk @ 0x#{offsets[i].to_s(16)}: No valid solutions!"
                    output.write(chunk)
                    i += 1
                    next
                else
                    puts "[*] Trying all #{possibilities.count} possible ways to make CRC 0x#{crc.to_s(16)} match..."
                end

                # try and fix the chunk if it's possible
                success = false
                possibilities.each do |combo|
                    new = chunk.dup
                    offset = 0
                    combo.each do |i|
                        new.insert(i + offset, "\r")
                        offset += 1
                    end
                    if Zlib.crc32(new[4..-5]) == crc
                        puts "[+] Fixed broken #{chunk[4..7]} chunk @ 0x#{offsets[i].to_s(16)}"
                        output.write(new)
                        success = true
                        break
                    end
                end
                if not success
                    puts "[!] Cannot fix broken #{chunk [4..7]} chunk @ 0x#{offsets[i].to_s(16)}: No valid solutions!"
                    output.write(chunk)
                end
                i += 1
            end
        end
    end
end